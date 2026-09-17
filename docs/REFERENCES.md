# References / provenance
調査日: 2026-09-16。ソース一式やBIOSを参考資料として同梱しない。

## BIOSDrain
https://github.com/F0bes/biosdrain/tree/92aa25f0764ffde1deb77acfd5cea90db3dcb631

確認箇所: dump.c、sysman_rpc.c、sysman/main.c、sysman/rom.c、sysman/sysman_rpc.h、imports.lst、Makefile、biosdrain.c、LICENSE.MD。

- dump.cはraw ROM0を0x400000 bytes取得する。file-levelのrom0:RESET等を結合する方式ではない。
- ROMs[0].StartAddressはrom device ImageStartから求める。BOOT ROM physical baseは0x1FC00000。今回の縮小層はそのuncached alias 0xBFC00000を固定使用。
- 元MEM_IO_BLOCK_SIZEは0x20000。今回のRPCは0x4000ずつ、IOP作業bufferを小さくして同期転送。
- 元のIOP double buffer、EE asynchronous wrapperを縮小してread-only同期RPCに再構成。最後のDMA完了・EE cache ownership・範囲検証を追加。
- 再利用/変更ファイル: ps2/sysman_client.c、ps2/iop/main.c。元著作権Copyright 2022 Ty Lamontagne (Fobes)とMIT許諾全文をps2/LICENSESに維持する。
- USB、hostファイル出力、その他周辺機器初期化、UI、フォントは取り込んでいない。

## PS2SDK / PS2DEV
調査SDK pin: https://github.com/ps2dev/ps2sdk/tree/be49dfb4e53fc9b5d11c3c90dd2dddc788196020

確認: ee/graph/include/graph.h、graph_vram.h、ee/graph/src/graph.c、ee/draw/include/draw.h・draw2d.h・draw_types.h、ee/draw/src/draw2d.c、cube sample、kernel cache/RPC/loadfile declarations、LICENSE。

graph_initializeは調査版ではinterlace/flicker-filterを有効にするので使わず、graph_set_mode等を明示的に呼ぶ。draw_rect_filledの座標biasをGS adapterで相殺し、portable rendererのexclusive矩形に揃える。APIの引数はビルド済みSDKでもコンパイル確認した。実際のGS pixel一致はPCSX2/実機待ち。

SDKの代表ライセンスはAFL-2.0。SDK/third-party libraryの各著作権表示はその上流に従う。SDKを改変/再配布せず外部依存として使用。参照ソース: https://github.com/ps2dev/ps2sdk 。リンク済みELF用にps2/LICENSES/PS2SDK-AFL-2.0.txtを同梱。

ビルド環境: https://github.com/ps2dev/ps2dev/releases/tag/latest のps2dev-windows-latest.tar.gz。
取得asset SHA256: 0340d272ce5e6f9d41a038bffa63dc4b916278999c98144b62196b80d14087ff。
このhashは取得したtoolchain archiveの識別子であり、移動するlatest URLそのものの固定を保証しない。GCC 15.2.0。Windows実行時は32-bit MinGW DLLが必要で、この作業ではwork内に隔離して使用した。

## GOROman / PS1 BIOS Video Ripper ZX
技術解説: https://gist.github.com/GOROman/050176a1e53c90850a4e5c0ad6306d01
配信receiver: https://goroman.github.io/ps1-bios-ripper-zx/
調査した実装: https://goroman.github.io/ps1-bios-ripper-zx/app.js?v=6
原案（はむ / Imaha486）へのリンクは上記解説から確認。

公開app.jsでPS1V header検査、frame inverse、palette sampling、周回のframe map管理、worker/WASMへの分離を確認した。GitHubのGOROman/ps1-bios-ripper-zx repositoryは調査時404で、PS1送信側ソース一式とライセンスを確認できなかった。配信JS/解説の思想のみを参考にし、コードやPS1の起動ディスクを取り込んでいない。

今回採用: カラーセル、位置/色校正、frameと全体CRC、再送周回。今回不採用: PS1 wire互換、LZSS、多数決/FEC、Web UI、worker/WASM、COLOR8。PS2Vは独立v1。

## FreeDVDBoot
https://github.com/CTurt/FreeDVDBoot/tree/ba7fa5bbda2ccd19c0a1c37ab99115183a2a1b27
READMEの起動・custom disc setup、DVD Player version依存を調査。ELF実装とは独立したboot packagingの参考。root LICENSEは調査treeで見つからず、同梱loader等のライセンスを一括推定しない。コード/ISOは取り込んでいない。将来packaging時に各同梱物を個別確認する。

調査した配信app.jsのSHA256: 15cfc261d716811e34c60a7a143a9a293aac4362596816ee351f0d055a5c7afa
