import csv
FX={'USD':0.91,'EUR':1.0}
C='24 Nov 2026'
NC='not checked this week'
rows=[]
def r(wave,round_,supplier,id_,item,qty,pn,link,price,cur,stock,checked,note):
    rows.append(dict(Wave=wave,Round=round_,Supplier=supplier,ID=id_,Item=item,Qty=qty,
      **{'Supplier part no.':pn,'Link':link,'Unit price':price,'Currency':cur,
      'Stock / lead time':stock,'Price checked':checked,'Status / note':note}))
# Wave 1
W1='1 - order this week (long lead)'
r(W1,'P0','Laifual (Alibaba store, quote)','ST-202','Strain-wave reducer LHT-17-100-U-III, hollow',2,'LHT-17-100-U-III','https://zjlaifual.en.alibaba.com/','','USD','Lead time: ask in the quote (spec 11.1: listings 5-35 days)',C,'D82: 2 units, both measured on P0. Listings: Laifual store hollow units USD 250-514; AliExpress LHT-17 USD 479.31. Ask for the LHT-17/14-100-U-III drawing + STEP with the quote (needed for ST-205, D85)')
r(W1,'P1','Laifual (Alibaba store, quote)','ST-201','Strain-wave reducer LHT-14-100-U-III, hollow',1,'LHT-14-100-U-III','https://zjlaifual.en.alibaba.com/','','USD','Quote now, buy after P0 test T2',C,'D82: buy after P0 test T2; ask in the same quote request')
r(W1,'P0+P1','Mouser (via JLCPCB Global sourcing)','ST-506','USB-C PD controller, port A (U3)',2,'595-TPS25751DREFR','https://www.mouser.com/c/?q=TPS25751DREFR',3.48,'USD','Mouser: two reads differ (78 / 0); 12,000 due 15 Jan 2027. DigiKey 0 until Oct 2027',C,'CRITICAL: buy first. Not needed to run P0 from the bench supply')
r(W1,'P0+P1','Mouser (via JLCPCB Global sourcing)','ST-507','USB-C PD source controller, port B (U6)',2,'595-TPS25752ASRSMR','https://www.mouser.com/c/?q=TPS25752',2.66,'USD','1,331 in stock',C,'BOM corrected to TPS25752ASRSMR (D84); pinout checked against the TPS25752A datasheet')
r(W1,'P0+P1','Mouser (via JLCPCB Global sourcing)','ST-508','Buck-boost converter, port B (U7)',2,'595-TPS55288RPMR','https://www.mouser.com/c/?q=TPS55288RPMR',6.10,'USD','3,085 in stock',C,'')
r(W1,'P0+P1','Mouser (via JLCPCB Global sourcing)','ST-514','IMU (U21)',2,'511-LSM6DSVTR','https://www.mouser.com/c/?q=LSM6DSVTR',5.15,'USD','16,284 in stock',C,'')
r(W1,'P0+P1','Mouser (via JLCPCB Global sourcing)','ST-513','Real-time clock (U23)',2,'428-203591-MG01 (RV-3028-C7 32.768kHz 1ppm TA QC)','https://www.mouser.com/c/?q=RV-3028-C7',2.41,'USD','0 in stock, 191,489 on order (no date shown)',C,'Not needed for P0: board can come with U23 empty (D83)')
r(W1,'P0+P1','Mouser (via JLCPCB Global sourcing)','ST-511','GNSS module (U24)',2,'377-MAX-M10S-00B','https://www.mouser.com/c/?q=MAX-M10S-00B',9.12,'USD','0 in stock; 14,712 due 4 Jan 2027; factory 18 weeks',C,'Not needed for P0; castellated, can be hand-soldered later (D83)')
r(W1,'P0+P1','Mouser (via JLCPCB Global sourcing)','ST-513','Clock backup cell (BT1)',2,'628-MS621FE-FL11E','https://www.mouser.com/c/?q=MS621FE-FL11E',2.51,'USD','3,899 in stock',C,'')
r(W1,'P0+P1','LCSC / JLCPCB parts library','ST-521','Magnetic encoder MT6835GT-STD-R (U1 on ST-520)',5,'C2932578','https://www.lcsc.com/product-detail/C2932578.html',3.5628,'USD','850 in stock',C,'BOM corrected from C2984637 (now the A10K variant) to C2932578 (D84)')
r(W1,'P0+P1','LCSC / JLCPCB parts library','ST-504','Stepper driver TMC2209-LA (U15, U17, U19)',6,'C465949','https://www.lcsc.com/product-detail/C465949.html',1.722,'USD','21 in stock',C,'Buy into your JLCPCB parts account before ordering the boards')
r(W1,'P0+P1','JLCPCB','ST-501','Mainboard, 6 layers, assembled both sides',2,'st-501 Gerbers + BOM + CPL','https://jlcpcb.com/',290,'USD','Board 5-7 days + assembly; waits for the sourced parts',NC,'D83. Estimate (Phase 4 fee structure); the order page gives the figure. 5 bare, 2 assembled. Large ICs below')
r(W1,'P0+P1','JLCPCB parts library','ST-502..510,515','Large ICs placed from stock: ESP32-S3-WROOM-1-N16R8 C2913202, RP2354A C41378174, BQ25792 C2862876, TPS61288 C5219223, TPS62932 C3032935, TPS563201 C116592, MMC5983MA C404329',2,'set','https://jlcpcb.com/parts',88,'USD','Stock checked at upload',NC,'About EUR 80 per set in the master parts list (Phase 4); LCSC numbers from the confirmed Phase 4 catalogue')
r(W1,'P0+P1','JLCPCB','ST-520','Cartridge board, 2 layers, assembled both sides',5,'st-520 Gerbers + BOM + CPL','https://jlcpcb.com/',90,'USD','As above',NC,'D83. Estimate; P0 uses 1, P1 3, 1 spare. Line total = whole order')
# Wave 2
W2='2 - P0 mechanics, this week'
r(W2,'P0','JLCCNC','ST-303','Head base plate (azimuth output, 3/8in socket)',1,'hardware/fab/cnc/ST-303.step + .pdf','https://jlccnc.com/',48,'USD','Instant quote',NC,'Phase 3 estimate; 6061-T6, bead-blast + clear anodise')
r(W2,'P0','JLCCNC','ST-208','Encoder reference tube, size 17',1,'ST-208.step + .pdf','https://jlccnc.com/',12,'USD','Instant quote',NC,'Phase 3 estimate')
r(W2,'P0','JLCCNC','ST-207','Motor plate with tension block',1,'ST-207.step + .pdf','https://jlccnc.com/',26,'USD','Instant quote',NC,'Phase 3 estimate')
r(W2,'P0','JLC3DP','ST-211','Cartridge housing, size 17 (FDM PA12-CF, black)',1,'ST-211 STL from hardware/cad/stl','https://jlc3dp.com/',3.00,'USD','72 h build',C,'D80. From USD 3.00; real price from the quote (115 g part)')
r(W2,'P0','JLC3DP','ST-212','Cartridge rear cover / encoder-board carrier (MJF PA12)',1,'ST-212 STL','https://jlc3dp.com/','','USD','72 h build',NC,'D80')
r(W2,'P0+P1','JLC3DP','ST-310','Azimuth body (MJF PA12, dyed black)',1,'ST-310-MJF.step','https://jlc3dp.com/',51,'USD','Instant quote',NC,'D81 (P0 rig in the real body). 184 g at USD 0.275/g (JLC3DP price since 13 Aug 2025); kept for P1')
r(W2,'P0+P1','JLC3DP','ST-315','Front bezel (MJF PA12)',1,'ST-315 STL','https://jlc3dp.com/',7,'USD','Instant quote',NC,'D81. 24 g at USD 0.275/g; kept for P1')
r(W2,'P0','StepperOnline (Germany warehouse)','ST-214','Stepper 17HS19-2004S1, 48 mm (azimuth)',1,'17HS19-2004S1','https://omc-stepperonline.com/nema-17-bipolar-59ncm-84oz-in-2a-42x48mm-4-wires-w-1m-cable-and-connector.html',12.79,'USD','DE warehouse 51 in stock; ships within 24 h',C,'USD 9.62 + 3.17 DE warehouse')
r(W2,'P1','StepperOnline (Germany warehouse)','ST-203','Stepper 17HE15-1504S, 38 mm (altitude, roll)',2,'17HE15-1504S','https://www.omc-stepperonline.com/e-series-nema-17-bipolar-42ncm-59-49oz-in-1-5a-42x42x38mm-4-wires-w-1m-cable-connector-17he15-1504s',6.12,'USD','DE warehouse 130 in stock',C,'USD 4.72 + 1.40 DE warehouse; same parcel as the P0 motor')
r(W2,'P0+P1','123-3D (Ireland)','ST-206','GT2 closed belt 200 mm, 9 mm',4,'123-3D GT2 9mm 200mm','https://www.123-3d.ie/123-3D-GT2-closed-timing-belt-9mm-200mm-i2753.html',4.50,'EUR','In stock',C,'P0 1, P1 2, 1 spare')
r(W2,'P0+P1','123-3D / Misumi','ST-204','GT2 pulley 20T, 9 mm, 5 mm bore, M4 set screws',4,'GT2-20T-W9-B5','https://www.123-3d.co.uk/123-3D-GT2-timing-belt-pulley-20-teeth-9mm-belt-bore-6-35m-GT2-20T-W9-B6-35-i4690.html','','EUR','',NC,'Pick the 5 mm bore on the page')
r(W2,'P0+P1','to be decided','ST-205','GT2 pulley 60T, 9 mm, bolts to the reducer input',4,'custom','','','EUR','Blocked until the Laifual drawing arrives',C,'D85: made once the Laifual drawing is in. Shopping-list link (RS 236-5741) is a 3 mm HTD pulley: do not buy')
r(W2,'P0+P1','magnet supplier','ST-209','Magnet 6 x 2.5 mm diametric N35SH',5,'','','','EUR','',NC,'Supplier to pick')
r(W2,'P0','JST via distributor','ST-530-AZ','Pre-crimped JST GH lead 28 AWG 305 mm',15,'AGHGH28K305','','','EUR','',NC,'P0 uses the full 305 mm length (mainboard on the bench)')
r(W2,'P0+P1','JST via distributor','ST-530','JST GH 15-way housing',6,'GHR-15V-S','','','EUR','',NC,'')
r(W2,'P0+P1','JST via distributor','ST-530','JST PH 4-way housing + crimp contacts',1,'PHR-4 (3) + SPH-002T-P0.5S (20)','','','EUR','',NC,'Motor plugs')
r(W2,'P0+P1','generic','ST-530','NTC bead 10 k B3950, 2 leads',3,'MF52-103 3950','','','EUR','',NC,'D46')
r(W2,'P0+P1','Fastener Express','ST-716/717','7075-T6 aluminium screws M3 x 45 (8) and M3 x 50 (24)',1,'set','https://www.fastener-express.com/',36.95,'USD','',NC,'Phase 3 pack price (50 pcs USD 36.95), not rechecked')
r(W2,'P0+P1','Accu / bolts.co.uk','ST-710..752','Stainless screws and washers, full P1 set (P0 uses steps 2-4)',1,'set per parts list','https://accu-components.com/',27,'EUR','',NC,'Phase 3 estimate')
r(W2,'P0+P1','3DJake (Ruthex)','ST-760..762','Heat-set inserts M3 100, M4 50, M5',1,'Ruthex','https://www.3djake.com/ruthex/threaded-insert-m3-100-pieces','','EUR','',NC,'')
r(W2,'P0+P1','any','ST-708','Loctite 243 and 638',1,'','','','EUR','',NC,'')
r(W2,'P0+P1','camera hardware supplier','ST-307','3/8in-16 stainless bushing, OD 12 x 8',2,'','','','EUR','',NC,'One in ST-303 for P0')
# Tools
WT='T - tools, this week'
r(WT,'P0','Elektor','tool','JOY-iT RD6006 bench supply bundle (0-60 V, 0-6 A, current limit)',1,'JT-RD6006 bundle','https://elektor.com/joy-it-rd6006-dc-power-supply-bundle-360-w',169.95,'EUR','',NC,'Incl. VAT; price from search snippet, page date not shown')
r(WT,'P0','Elektor','tool','USB-C PD tester FNIRSI FNB58 (Bluetooth)',1,'FNB58 BT','https://www.elektor.com/products/fnirsi-fnb58-usb-tester-with-bluetooth',49.95,'EUR','',NC,'Incl. VAT')
r(WT,'P0','RS Portugal','tool','Raspberry Pi Debug Probe',1,'RS 219-258','https://pt.rs-online.com/web/p/placas-hat-y-complementos-para-raspberry-pi/0219258',11.35,'EUR','',NC,'Excl. VAT')
r(WT,'P0','Tag-Connect','tool','TC2030-IDC-NL cable (to J5/J6)',1,'TC2030-IDC-NL','https://www.tag-connect.com/product/tc2030-idc-nl',33.95,'USD','Available',C,'')
r(WT,'P0','Kiwi Electronics','tool','Crimp tool Engineer PA-09 (JST GH/PH)',1,'EN-PA09','https://www.kiwi-electronics.com/en/tools-machines-155/jst-crimping-tool-pa-09-916',39.99,'EUR','39 in stock',NC,'Excl. VAT')
r(WT,'P0','RS','tool','Dial indicator 0.001 mm (test T1)',1,'RS 180-9467','https://ie.rs-online.com/web/p/dial-indicators/1809467',149.35,'EUR','In stock',NC,'Incl. VAT; the magnetic base is its own line below')
r(WT,'P0','eleshop.eu','tool','Multimeter UNI-T UT161E (True RMS, 22,000 counts)',1,'ELE004627','https://eleshop.eu/uni-t-ut161e.html',80.34,'EUR','',NC,'Excl. VAT; successor of the UT61E. D86: you own no bench tools')
r(WT,'P0','eleshop.eu','tool','Soldering + hot-air station Atten ST-8802 (65 W iron, 800 W hot air)',1,'ST-8802','https://eleshop.eu/atten-multifunctional-stations.html',117.00,'EUR','',NC,'Excl. VAT. For U23/U24, thermistor leads and the heat-set inserts (add an insert tip)')
r(WT,'P0','TME','tool','Oscilloscope Hantek DSO2C10 (2 ch, 100 MHz)',1,'DSO2C10','https://www.tme.eu/om/en/details/dso2c10/digital-oscilloscopes/hantek/',192.37,'EUR','66 in TME stock',NC,'Net price. Stage C ripple and the port B load step')
r(WT,'P0','Waveshare','tool','USB-to-UART adapter CP2102, 3.3 V, USB-C',1,'SKU 20644','https://www.waveshare.com/product/cp2102-usb-uart-board-type-c.htm',4.36,'EUR','',NC,'ESP32 console through J5 if USB does not enumerate')
r(WT,'P0','RS','tool','Torque screwdriver Wera 7400, 0.3-1.2 Nm, 1/4in bits',1,'RS 738-3576 (05074730001)','https://ie.rs-online.com/web/p/torque-screwdrivers/7383576',137.26,'EUR','',NC,'Excl. VAT. Covers the 0.3-1.2 Nm joints (most of steps 2-4)')
r(WT,'P0','RS','tool','Torque screwdriver Wiha, 0.8-5 Nm, hex, 4 mm drive',1,'RS 238-6146 (26463)','https://ie.rs-online.com/web/p/torque-screwdrivers/2386146',185.30,'EUR','',NC,'Excl. VAT. For the 1.5-4.5 Nm joints; needs 2 / 2.5 / 3 mm hex bits for 4 mm drive')
r(WT,'P0','RS','tool','Magnetic base for the dial indicator (400 N, 8 mm stem)',1,'RS PRO 261-4517','https://uk.rs-online.com/web/p/bases-arms/2614517','','EUR','',NC,'GBP 41.74 excl. VAT at RS UK; RS Portugal shows the EUR price at checkout')
r(WT,'P0','any','tool','Not priced yet: hex keys 2/2.5/3 mm and bits, digital caliper, IR thermometer, small vice, laser module, power resistors 10 ohm 50 W + 3.3 ohm 10 W, USB-A to USB-C cable, 45 W USB-C PD charger + e-marked cable, flux, 0.3 mm solder, fine tweezers, heat-set insert tip',1,'','','','EUR','',NC,'D86. I price these on request, or buy locally')
# P1
W3='3 - P1, after P0 Stage D passes'
r(W3,'P1','Mouser','tool','TI EV2400 gauge interface (bqStudio)',1,'595-EV2400','https://www.mouser.com/c/?q=EV2400',258.03,'USD','430 in stock (page also showed an error)',C,'Gauge is on the battery board: P1 only')
r(W3,'P1','JLCPCB','ST-602','Battery board, assembled top',2,'st-602 Gerbers + BOM + CPL','https://jlcpcb.com/',97,'USD','',NC,'D83. Phase 4 estimate')
r(W3,'P1','LCSC / JLCPCB parts library','ST-603','Gauge BQ40Z50RSMR-R2',2,'C2845123','https://www.lcsc.com/product-detail/C2845123.html',1.9707,'USD','14,832 in stock',C,'')
r(W3,'P1','DigiKey','ST-604','Three-terminal fuse ITV4030L0815NR',2,'ITV4030L0815NR','',5.40,'USD','Mouser: non-stocked, MOQ 5,000, 15 weeks',C,'Price is the Phase 4 DigiKey figure, not rechecked; check DigiKey stock')
r(W3,'P1','NKON','ST-601','Molicel INR-21700-P50B',4,'P50B','https://www.nkon.nl/novat/rechargeable/molicel-inr21700-p50b-5000mah-50a.html',4.95,'EUR','Stock not shown',C,'EUR 4.45 from 11 pcs; VAT basis not stated on the page')
r(W3,'P1','JLCCNC','ST-301,302,331,305,312,313,207,208,215','Remaining CNC set',1,'hardware/fab/cnc/*.step + .pdf','https://jlccnc.com/',501,'USD','Instant quote',NC,'Phase 3 estimate (587 set minus the P0 parts)')
r(W3,'P1','JLC3DP','ST-210,211,311,2xx-6xx','Tower (MJF), 2 cartridge housings (PA12-CF), all other printed parts',1,'hardware/cad/stl','https://jlc3dp.com/','','USD','',NC,'D80: all printed parts from JLC3DP; materials for the ASA, TPU and PETG parts chosen at the P1 order')
r(W3,'P1','B&H / dealer','ST-314','Arca clamp Sunwayfoto DDC-60i',1,'DDC-60i','',31.85,'EUR','',NC,'Master parts list price; page could not be read this week')
r(W3,'P1','various','ST-304..333','Hinge pin, dowels, coin screws, thumb screws, V-rings, O-ring, PC window',1,'see hardware/fab/shopping-list.csv','','','EUR','',NC,'')
r(W3,'P1','JST / generic','ST-530/531/532','Remaining harness parts (altitude, roll PTFE wire, XT30, power and data leads, jack)',1,'see harness-purchase-list.csv','','','EUR','',NC,'')
for x in rows:
    p=x['Unit price']
    if p=='' : x['Unit price EUR']='';x['Line total EUR']=''
    else:
        e=round(p*FX[x['Currency']],2); x['Unit price EUR']=e
        q=x['Qty'] if not str(x['Supplier part no.']).startswith('st-') else 1
        x['Line total EUR']=round(e*q,2)
cols=['Wave','Round','Supplier','ID','Item','Qty','Supplier part no.','Link','Unit price','Currency','Unit price EUR','Line total EUR','Stock / lead time','Price checked','Status / note']
with open('hardware/bom/order-plan-p0-p1.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows(rows)
tot={}
for x in rows:
    if x['Line total EUR']!='': tot[x['Wave']]=tot.get(x['Wave'],0)+x['Line total EUR']
print(len(rows),{k:round(v,2) for k,v in tot.items()})
