package pt.brunomonte.startracker;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.webkit.GeolocationPermissions;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.window.OnBackInvokedDispatcher;

import java.io.IOException;
import java.io.InputStream;

import pt.brunomonte.startracker.camera.CameraBridge;

/**
 * Star Tracker for Android (decision D72): the shared UI (app/ui + app/shared, copied into assets/web by Gradle)
 * in a WebView, with two bridges: window.StNative (discovery, BLE, keep-awake, location, files; StNative.java) and
 * window.CameraNative (the Sony camera code reused from Benro-Polaris-Controller). The pages are served from
 * https://appassets.androidplatform.net/ so ES modules load; ws:// and http:// to the head are allowed (mixed content).
 */
public class MainActivity extends Activity {

    static final String HOST = "appassets.androidplatform.net";
    private static final String HOME = "https://" + HOST + "/web/ui/index.html";
    private static final int PERMS = 4713, FILE_PICK = 4714;

    private WebView webView;
    private CameraBridge cameraBridge;
    private ValueCallback<Uri[]> fileCallback;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        webView = new WebView(this);
        setContentView(webView);
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setGeolocationEnabled(true);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);   // ws:// and http:// to the head on the local network
        s.setMediaPlaybackRequiresUserGesture(true);
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest req) {
                Uri u = req.getUrl();
                if (!HOST.equals(u.getHost()) || u.getPath() == null) return null;
                try {
                    InputStream in = getAssets().open(u.getPath().substring(1));
                    WebResourceResponse r = new WebResourceResponse(mime(u.getPath()), "utf-8", in);
                    r.setResponseHeaders(java.util.Collections.singletonMap("Cache-Control", "no-cache"));
                    return r;
                } catch (IOException e) {
                    return new WebResourceResponse("text/plain", "utf-8", 404, "Not found", null, null);
                }
            }
        });
        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onGeolocationPermissionsShowPrompt(String origin, GeolocationPermissions.Callback cb) {
                cb.invoke(origin, checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED, false);
            }

            @Override
            public boolean onShowFileChooser(WebView v, ValueCallback<Uri[]> cb, FileChooserParams p) {
                fileCallback = cb;                                       // the .stfw file on the Firmware screen
                Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType("*/*");
                startActivityForResult(i, FILE_PICK);
                return true;
            }
        });
        webView.addJavascriptInterface(new StNative(this, webView), "StNative");
        cameraBridge = new CameraBridge(this);
        webView.addJavascriptInterface(cameraBridge, "CameraNative");
        if (savedInstanceState != null) webView.restoreState(savedInstanceState);
        else webView.loadUrl(HOME);
        if (Build.VERSION.SDK_INT >= 33) {
            getOnBackInvokedDispatcher().registerOnBackInvokedCallback(OnBackInvokedDispatcher.PRIORITY_DEFAULT, this::goBack);
        }
        askPermissions();
        cameraBridge.onIntent(getIntent());
    }

    static String mime(String path) {
        if (path.endsWith(".html")) return "text/html";
        if (path.endsWith(".js") || path.endsWith(".mjs")) return "text/javascript";
        if (path.endsWith(".css")) return "text/css";
        if (path.endsWith(".woff2")) return "font/woff2";
        if (path.endsWith(".svg")) return "image/svg+xml";
        if (path.endsWith(".png")) return "image/png";
        if (path.endsWith(".json")) return "application/json";
        return "application/octet-stream";
    }

    void askPermissions() {
        java.util.List<String> want = new java.util.ArrayList<>();
        want.add(Manifest.permission.ACCESS_FINE_LOCATION);
        want.add(Manifest.permission.ACCESS_COARSE_LOCATION);
        if (Build.VERSION.SDK_INT >= 31) { want.add(Manifest.permission.BLUETOOTH_SCAN); want.add(Manifest.permission.BLUETOOTH_CONNECT); }
        if (Build.VERSION.SDK_INT >= 33) want.add(Manifest.permission.POST_NOTIFICATIONS);
        java.util.List<String> missing = new java.util.ArrayList<>();
        for (String p : want) if (checkSelfPermission(p) != PackageManager.PERMISSION_GRANTED) missing.add(p);
        if (!missing.isEmpty()) requestPermissions(missing.toArray(new String[0]), PERMS);
    }

    @Override
    protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (request == FILE_PICK && fileCallback != null) {
            fileCallback.onReceiveValue(result == RESULT_OK && data != null && data.getData() != null ? new Uri[]{data.getData()} : null);
            fileCallback = null;
        }
    }

    private void goBack() {
        if (webView.canGoBack()) webView.goBack();
        else finish();
    }

    @Override
    @SuppressWarnings("deprecation")
    public void onBackPressed() { goBack(); }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        cameraBridge.onIntent(intent);
    }

    @Override
    protected void onSaveInstanceState(Bundle out) {
        super.onSaveInstanceState(out);
        webView.saveState(out);
    }

    /** Status and navigation bars follow the display mode (Day light, Night dark, Red black). */
    void applyTheme(String t) {
        int c = "day".equals(t) ? 0xFF5F8FC4 : "red".equals(t) ? 0xFF000000 : 0xFF0F1A2E;
        getWindow().setStatusBarColor(c);
        getWindow().setNavigationBarColor(c);
    }
}
