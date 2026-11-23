// ptpwpd.dll: PTP commands to a camera through Windows Portable Devices.
//
// Windows claims a USB camera (like a Sony A7R V in PC Remote mode) with
// its own MTP/PTP driver, so the camera cannot be opened directly. WPD's
// "MTP extension" commands let an app send any PTP operation, vendor ones
// included, with a data phase in either direction. This is the method
// digiCamControl uses. Called from Python (polaris_desktop/ptp_win.py)
// through ctypes; every function is safe to call from any thread.

#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <PortableDeviceApi.h>
#include <PortableDevice.h>
#include <cstdio>
#include <string>
#include <algorithm>
#include <vector>

#pragma comment(lib, "PortableDeviceGUIDs.lib")
#pragma comment(lib, "Ole32.lib")

#define EXPORT extern "C" __declspec(dllexport)

// WPD MTP extension commands and properties (category "MTPX",
// {4D545058-1A2E-4106-A357-771E0819FC56}), defined here because not every
// Windows SDK header set exposes them. Values from the WPD documentation.
namespace mtpx {
constexpr GUID kCategory = {0x4D545058, 0x1A2E, 0x4106, {0xA3, 0x57, 0x77, 0x1E, 0x08, 0x19, 0xFC, 0x56}};
constexpr PROPERTYKEY key(DWORD pid) { return PROPERTYKEY{kCategory, pid}; }
// Commands
constexpr PROPERTYKEY EXECUTE_WITHOUT_DATA_PHASE = key(12);
constexpr PROPERTYKEY EXECUTE_WITH_DATA_TO_READ = key(13);
constexpr PROPERTYKEY EXECUTE_WITH_DATA_TO_WRITE = key(14);
constexpr PROPERTYKEY READ_DATA = key(15);
constexpr PROPERTYKEY WRITE_DATA = key(16);
constexpr PROPERTYKEY END_DATA_TRANSFER = key(17);
// Properties
constexpr PROPERTYKEY OPERATION_CODE = key(1001);
constexpr PROPERTYKEY OPERATION_PARAMS = key(1002);
constexpr PROPERTYKEY RESPONSE_CODE = key(1003);
constexpr PROPERTYKEY RESPONSE_PARAMS = key(1004);
constexpr PROPERTYKEY TRANSFER_CONTEXT = key(1006);
constexpr PROPERTYKEY TRANSFER_TOTAL_DATA_SIZE = key(1007);
constexpr PROPERTYKEY TRANSFER_NUM_BYTES_TO_READ = key(1008);
constexpr PROPERTYKEY TRANSFER_NUM_BYTES_READ = key(1009);
constexpr PROPERTYKEY TRANSFER_NUM_BYTES_TO_WRITE = key(1010);
constexpr PROPERTYKEY TRANSFER_NUM_BYTES_WRITTEN = key(1011);
constexpr PROPERTYKEY TRANSFER_DATA = key(1012);
constexpr PROPERTYKEY OPTIMAL_TRANSFER_BUFFER_SIZE = key(1013);
}  // namespace mtpx

namespace {

void ensureCom() {
    // Multithreaded apartment on every calling thread; repeated calls are harmless.
    CoInitializeEx(nullptr, COINIT_MULTITHREADED);
}

void setError(wchar_t* err, int len, const wchar_t* what, HRESULT hr) {
    if (err && len > 0) swprintf_s(err, len, L"%s (0x%08X)", what, static_cast<unsigned>(hr));
}

/** Same, naming the PTP operation, e.g. "Camera command 0x9201 failed (0x8007065D)". */
void setOpError(wchar_t* err, int len, const wchar_t* what, unsigned op, HRESULT hr) {
    if (err && len > 0)
        swprintf_s(err, len, L"%s 0x%04X failed (0x%08X)", what, op, static_cast<unsigned>(hr));
}

template <class T>
void release(T*& p) {
    if (p) {
        p->Release();
        p = nullptr;
    }
}

HRESULT newValues(IPortableDeviceValues** v) {
    return CoCreateInstance(CLSID_PortableDeviceValues, nullptr, CLSCTX_INPROC_SERVER, IID_PPV_ARGS(v));
}

/** Starts a command: category + id taken from a WPD command key. */
HRESULT commandValues(const PROPERTYKEY& command, IPortableDeviceValues** v) {
    HRESULT hr = newValues(v);
    if (FAILED(hr)) return hr;
    (*v)->SetGuidValue(WPD_PROPERTY_COMMON_COMMAND_CATEGORY, command.fmtid);
    (*v)->SetUnsignedIntegerValue(WPD_PROPERTY_COMMON_COMMAND_ID, command.pid);
    return S_OK;
}

/** Sends a command and checks the driver's own result code. */
HRESULT send(IPortableDevice* dev, IPortableDeviceValues* params, IPortableDeviceValues** results) {
    HRESULT hr = dev->SendCommand(0, params, results);
    if (FAILED(hr)) return hr;
    HRESULT inner = S_OK;
    if (SUCCEEDED((*results)->GetErrorValue(WPD_PROPERTY_COMMON_HRESULT, &inner)) && FAILED(inner)) {
        release(*results);
        return inner;
    }
    return S_OK;
}

void readResponse(IPortableDeviceValues* results, unsigned* code, unsigned* respParams, int* nResp) {
    ULONG rc = 0;
    results->GetUnsignedIntegerValue(mtpx::RESPONSE_CODE, &rc);
    *code = rc;
    *nResp = 0;
    IPortableDevicePropVariantCollection* coll = nullptr;
    if (SUCCEEDED(results->GetIPortableDevicePropVariantCollectionValue(mtpx::RESPONSE_PARAMS, &coll)) && coll) {
        DWORD n = 0;
        coll->GetCount(&n);
        for (DWORD i = 0; i < n && i < 5; i++) {
            PROPVARIANT pv;
            PropVariantInit(&pv);
            if (SUCCEEDED(coll->GetAt(i, &pv))) respParams[(*nResp)++] = pv.ulVal;
            PropVariantClear(&pv);
        }
        release(coll);
    }
}

}  // namespace

/**
 * Lists portable devices as lines "id<TAB>name<TAB>manufacturer\n" into buf.
 * Returns the number of devices, or -1 on error.
 */
EXPORT int ptp_list(wchar_t* buf, int buflen) {
    ensureCom();
    if (buf && buflen > 0) buf[0] = 0;
    IPortableDeviceManager* mgr = nullptr;
    if (FAILED(CoCreateInstance(CLSID_PortableDeviceManager, nullptr, CLSCTX_INPROC_SERVER, IID_PPV_ARGS(&mgr)))) return -1;
    mgr->RefreshDeviceList();
    DWORD n = 0;
    mgr->GetDevices(nullptr, &n);
    std::vector<PWSTR> ids(n);
    if (n > 0 && FAILED(mgr->GetDevices(ids.data(), &n))) {
        release(mgr);
        return -1;
    }
    std::wstring out;
    for (DWORD i = 0; i < n; i++) {
        std::wstring name, maker;
        DWORD len = 0;
        if (SUCCEEDED(mgr->GetDeviceFriendlyName(ids[i], nullptr, &len)) && len > 0) {
            name.resize(len);
            mgr->GetDeviceFriendlyName(ids[i], &name[0], &len);
            name.resize(wcslen(name.c_str()));
        }
        len = 0;
        if (SUCCEEDED(mgr->GetDeviceManufacturer(ids[i], nullptr, &len)) && len > 0) {
            maker.resize(len);
            mgr->GetDeviceManufacturer(ids[i], &maker[0], &len);
            maker.resize(wcslen(maker.c_str()));
        }
        out += ids[i];
        out += L"\t" + name + L"\t" + maker + L"\n";
        CoTaskMemFree(ids[i]);
    }
    release(mgr);
    if (buf && buflen > 0) wcsncpy_s(buf, buflen, out.c_str(), _TRUNCATE);
    return static_cast<int>(n);
}

/** Opens a device by id. Returns a handle, or null with err filled in. */
EXPORT void* ptp_open(const wchar_t* id, wchar_t* err, int errlen) {
    ensureCom();
    IPortableDeviceValues* client = nullptr;
    HRESULT hr = newValues(&client);
    if (FAILED(hr)) {
        setError(err, errlen, L"Cannot create client info", hr);
        return nullptr;
    }
    client->SetStringValue(WPD_CLIENT_NAME, L"Polaris Control");
    client->SetUnsignedIntegerValue(WPD_CLIENT_MAJOR_VERSION, 1);
    client->SetUnsignedIntegerValue(WPD_CLIENT_MINOR_VERSION, 0);
    client->SetUnsignedIntegerValue(WPD_CLIENT_REVISION, 0);
    client->SetUnsignedIntegerValue(WPD_CLIENT_SECURITY_QUALITY_OF_SERVICE, SECURITY_IMPERSONATION);
    IPortableDevice* dev = nullptr;
    // Free-threaded object: usable from the Python threads that call us.
    hr = CoCreateInstance(CLSID_PortableDeviceFTM, nullptr, CLSCTX_INPROC_SERVER, IID_PPV_ARGS(&dev));
    if (SUCCEEDED(hr)) hr = dev->Open(id, client);
    release(client);
    if (FAILED(hr)) {
        release(dev);
        setError(err, errlen, L"Cannot open the camera", hr);
        return nullptr;
    }
    return dev;
}

EXPORT void ptp_close(void* handle) {
    ensureCom();
    IPortableDevice* dev = static_cast<IPortableDevice*>(handle);
    if (dev) {
        dev->Close();
        dev->Release();
    }
}

EXPORT void ptp_free(unsigned char* p) {
    if (p) CoTaskMemFree(p);
}

/**
 * Runs one PTP operation.
 *   dataOut/outLen: data sent to the camera (null for none).
 *   wantData: 1 when the operation returns data; it is returned in
 *   *dataIn/*inLen (free it with ptp_free).
 * Returns the PTP response code (0x2001 = OK), or -1 with err filled in.
 */
EXPORT int ptp_transact(void* handle, unsigned op, const unsigned* params, int nparams,
                        const unsigned char* dataOut, unsigned outLen, int wantData,
                        unsigned char** dataIn, unsigned* inLen,
                        unsigned* respParams, int* nResp, wchar_t* err, int errlen) {
    ensureCom();
    IPortableDevice* dev = static_cast<IPortableDevice*>(handle);
    if (dataIn) *dataIn = nullptr;
    if (inLen) *inLen = 0;
    *nResp = 0;
    if (!dev) {
        setError(err, errlen, L"Camera not open", E_POINTER);
        return -1;
    }

    const PROPERTYKEY& start = dataOut ? mtpx::EXECUTE_WITH_DATA_TO_WRITE
                             : wantData ? mtpx::EXECUTE_WITH_DATA_TO_READ
                                        : mtpx::EXECUTE_WITHOUT_DATA_PHASE;
    IPortableDeviceValues* cmd = nullptr;
    IPortableDeviceValues* res = nullptr;
    IPortableDevicePropVariantCollection* plist = nullptr;
    HRESULT hr = commandValues(start, &cmd);
    if (SUCCEEDED(hr)) {
        cmd->SetUnsignedIntegerValue(mtpx::OPERATION_CODE, op);
        hr = CoCreateInstance(CLSID_PortableDevicePropVariantCollection, nullptr, CLSCTX_INPROC_SERVER, IID_PPV_ARGS(&plist));
    }
    if (SUCCEEDED(hr)) {
        for (int i = 0; i < nparams; i++) {
            PROPVARIANT pv;
            PropVariantInit(&pv);
            pv.vt = VT_UI4;
            pv.ulVal = params[i];
            plist->Add(&pv);
        }
        cmd->SetIPortableDevicePropVariantCollectionValue(mtpx::OPERATION_PARAMS, plist);
        if (dataOut) cmd->SetUnsignedLargeIntegerValue(mtpx::TRANSFER_TOTAL_DATA_SIZE, outLen);
        hr = send(dev, cmd, &res);
    }
    release(plist);
    release(cmd);
    if (FAILED(hr)) {
        setOpError(err, errlen, L"Camera command", op, hr);
        return -1;
    }

    unsigned code = 0;
    if (!dataOut && !wantData) {
        readResponse(res, &code, respParams, nResp);
        release(res);
        return static_cast<int>(code);
    }

    // Data phase: the driver gives a context string for the transfer.
    PWSTR context = nullptr;
    ULONGLONG total = 0;
    ULONG optimal = 0;
    res->GetStringValue(mtpx::TRANSFER_CONTEXT, &context);
    res->GetUnsignedLargeIntegerValue(mtpx::TRANSFER_TOTAL_DATA_SIZE, &total);
    res->GetUnsignedIntegerValue(mtpx::OPTIMAL_TRANSFER_BUFFER_SIZE, &optimal);
    release(res);
    if (!context) {
        setOpError(err, errlen, L"Camera transfer context for", op, E_UNEXPECTED);
        return -1;
    }

    std::vector<unsigned char> got;
    if (dataOut) {
        hr = commandValues(mtpx::WRITE_DATA, &cmd);
        if (SUCCEEDED(hr)) {
            cmd->SetStringValue(mtpx::TRANSFER_CONTEXT, context);
            cmd->SetUnsignedIntegerValue(mtpx::TRANSFER_NUM_BYTES_TO_WRITE, outLen);
            cmd->SetBufferValue(mtpx::TRANSFER_DATA, const_cast<BYTE*>(dataOut), outLen);
            hr = send(dev, cmd, &res);
            release(res);
        }
        release(cmd);
    } else {
        ULONG chunk = optimal ? optimal : 256 * 1024;
        if (chunk < 64 * 1024) chunk = 64 * 1024;
        std::vector<BYTE> empty(chunk);
        got.reserve(static_cast<size_t>(total));
        while (SUCCEEDED(hr) && got.size() < total) {
            ULONG want = static_cast<ULONG>(std::min<ULONGLONG>(chunk, total - got.size()));
            hr = commandValues(mtpx::READ_DATA, &cmd);
            if (FAILED(hr)) break;
            cmd->SetStringValue(mtpx::TRANSFER_CONTEXT, context);
            cmd->SetUnsignedIntegerValue(mtpx::TRANSFER_NUM_BYTES_TO_READ, want);
            cmd->SetBufferValue(mtpx::TRANSFER_DATA, empty.data(), want);
            hr = send(dev, cmd, &res);
            release(cmd);
            if (FAILED(hr)) break;
            ULONG read = 0;
            BYTE* p = nullptr;
            DWORD cb = 0;
            res->GetUnsignedIntegerValue(mtpx::TRANSFER_NUM_BYTES_READ, &read);
            if (SUCCEEDED(res->GetBufferValue(mtpx::TRANSFER_DATA, &p, &cb)) && p) {
                got.insert(got.end(), p, p + std::min<DWORD>(read, cb));
                CoTaskMemFree(p);
            }
            release(res);
            if (read == 0) break;
        }
    }

    // End of transfer: this carries the PTP response.
    HRESULT endHr = commandValues(mtpx::END_DATA_TRANSFER, &cmd);
    if (SUCCEEDED(endHr)) {
        cmd->SetStringValue(mtpx::TRANSFER_CONTEXT, context);
        endHr = send(dev, cmd, &res);
        if (SUCCEEDED(endHr)) readResponse(res, &code, respParams, nResp);
        release(res);
    }
    release(cmd);
    CoTaskMemFree(context);
    if (FAILED(hr) || FAILED(endHr)) {
        setOpError(err, errlen, L"Camera data transfer for", op, FAILED(hr) ? hr : endHr);
        return -1;
    }
    if (!dataOut && dataIn && inLen) {
        *inLen = static_cast<unsigned>(got.size());
        if (!got.empty()) {
            *dataIn = static_cast<unsigned char*>(CoTaskMemAlloc(got.size()));
            if (!*dataIn) {
                setError(err, errlen, L"Out of memory", E_OUTOFMEMORY);
                return -1;
            }
            memcpy(*dataIn, got.data(), got.size());
        }
    }
    return static_cast<int>(code);
}
