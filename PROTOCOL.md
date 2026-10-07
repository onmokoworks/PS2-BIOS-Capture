# PS2V protocol v1 (experimental, COLOR4 RAW)

全多byte整数はlittle-endian unsigned。CRCはCRC-32/ISO-HDLC (reflected polynomial 0xEDB88320, init/xorout 0xFFFFFFFF; Python zlib.crc32)。テストベクトル `123456789` → CBF43926。

| offset | bytes | field |
|---:|---:|---|
|0|4|ASCII PS2V|
|4|1|version=1|
|5|1|object type: TEST=0 ROM0=1; 2..5 reserved|
|6|1|color mode=4 (COLOR8未実装)|
|7|1|flags=0 (RAW)|
|8|4|session id|
|12|4|frame index (0 based)|
|16|4|frame index XOR FFFFFFFF|
|20|4|frame count|
|24|4|payload length|
|28|4|source offset (object relative)|
|32|4|source size|
|36|4|encoded size (=source size)|
|40|4|source CRC32|
|44|4|frame CRC32|
|48|0..132|payload|

frame CRC対象はheader[0:44] + payload（CRC自身とpaddingを除く）。headerを含めることでsession、offset、長さの破損も検出する。180 bytesまでゼロpadding。empty objectは1 frame、payload=0、CRC=0。source sizeはMVP受信上限16 MiB。count=max(1,ceil(size/132)); offset=index*132; len=min(132,size-offset)。これら全関係を厳密に検証する。

## pixels と symbols
320×224 RGB、background=(0,0,0)。座標は左上原点、矩形は右下exclusive。
- finderの外枠: (16,12),(288,12),(16,196),(288,196)に16×16白。
- 各finder内側: inset4の8×8黒、その内側inset6の4×4白。中心=(24,20),(296,20),(24,204),(296,204)。
- calibration: x=64+48*k, y=12, width32,height16, k=0..3。
- data: x=16,y=32,36 columns×20 rows、各8×8 pixels。row-major、720 cells=180 bytes。
- palette RGB: 0=(32,32,32), 1=(224,224,224), 2=(224,192,32), 3=(32,64,224)。
- 各byteはbit7..6,5..4,3..2,1..0の順に4 cellsへ。

receiverは4 finderのnested contoursから位置を求め、homographyで基準座標へ戻す。校正patchのRGB平均に最も近い色へ、セル中心3×3 pixelsの平均を分類する。四隅を失うcropは復旧対象外。背景以外の任意の映像や大回転への汎用検出器ではない。色が潰れた場合やCRC不一致は採用せず周回を待つ。

## sessionと保存
初回CRC合格frameで (version,type,mode,flags,session,count,size,encoded,source CRC) を固定。相違は混在させず拒否。indexごとにpacketを保存、再起動時にも全packetを再検証。同じindex/同じ内容は重複、同じindex/異内容は拒否。全indexが揃いサイズ・source CRC一致後のみ完成binaryを生成。CRCは伝送エラー検出であり、認証・暗号ではない。

PS2は最終frameの次にindex0へ戻り無期限送信。既定6 VBlank/frame。4 MiBで31,776 frames、理想約53分/周（59.94Hz、計算描画等の追加時間を除く）。このMVPは帯域よりセル安定性を優先。COLOR8/圧縮/FECのflagsは予約せず、将来version更新で設計する。

## Version 2: runtime density profiles

ヘッダー構造とCRC方式はv1と同じ。byte4=2、byte7はflagsではなくgrid profile IDを表す。COLOR4 RAWのみで、encoded size=source size。v1は引き続きbyte7=0・180 bytes固定で受信可能。

|profile|columns×rows|cell pixels|packet bytes|payload capacity|
|---:|---:|---:|---:|---:|
|0|36×20|8×8|180|132|
|1|48×26|6×6|312|264|
|2|72×40|4×4|720|672|

全profileのdata左上は(16,32)、finder/calibrationはv1と同じ。profile1は下端y=188、他は192。余った領域は黒。count=max(1,ceil(size/capacity))、offset=index*capacity、len=min(capacity,size-offset)。CRC後のゼロpaddingを含めpacket bytes固定。

receiverは3種類のサンプリングを試し、復号したヘッダーのprofileと採用したgridが一致し、frame CRCが通った場合のみ採用する。未知profile/サイズ関係の不整合は拒否。速度だけの変更は同sessionを維持する。密度変更は新session・index0から開始し、受信途中の異profileデータは混ぜない。デスクトップreceiverは設定変更を検出し、別checkpointセットへ切り替える。

自動送信は標準profileで0.1/0.2/0.3秒の周回を繰り返す固定schedule。受信品質に応じた自動最適化ではない。コントローラー操作は[INTERACTIVE](docs/INTERACTIVE.md)参照。
