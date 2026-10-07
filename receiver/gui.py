"""Native desktop capture/receiver. Run with python -m receiver.gui."""
import argparse
from collections import Counter
from pathlib import Path
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
from PIL import Image, ImageTk
from .capture import png_frames, video_frames
from .codec import decode_image
from .live import Transfer
from .protocol import GRIDS, DecodeError


def devices():
    try:
        from pygrabber.dshow_graph import FilterGraph
        return [(i, name) for i, name in enumerate(FilterGraph().get_input_devices())]
    except (ImportError, OSError, RuntimeError):
        return [(i, f'カメラ {i}') for i in range(5)]


class App:
    def __init__(self, root, args):
        self.root, self.args = root, args
        self.events = queue.Queue()
        self.preview = None
        self.worker = None
        self.stop = threading.Event()
        self.output_file = None
        self.image_ref = None
        root.title('PS2 Video Backup — キャプチャ受信')
        root.geometry('1000x780')
        root.minsize(820, 650)
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.status = tk.StringVar(value='キャプチャ機器を選んで「受信開始」を押してください。')
        self.counts = tk.StringVar(value='受信 0 / —　　欠落 —　　CRCエラー 0')
        self.details = tk.StringVar(value='PS2のカラーセル画面を待っています。')
        self.byte_counts = tk.StringVar(value='受信済み 0 bytes')
        self.byte_range = tk.StringVar(value='直近の受信範囲 —　　先頭の欠落位置 —')
        self.hex_preview = tk.StringVar(value='CRC合格フレームの先頭32 bytesをここに表示します。')
        self.output_dir = tk.StringVar(value=str(Path(args.output_dir).resolve()))
        outer = ttk.Frame(root, padding=14)
        outer.pack(fill='both', expand=True)
        top = ttk.Frame(outer)
        top.pack(fill='x')
        ttk.Label(top, text='キャプチャ機器').pack(side='left', padx=(0, 8))
        self.device = ttk.Combobox(top, state='readonly', width=43)
        self.device.pack(side='left', fill='x', expand=True)
        self.refresh_button = ttk.Button(top, text='再検索', command=self.refresh)
        self.refresh_button.pack(side='left', padx=8)
        self.start_button = ttk.Button(top, text='受信開始', command=self.start)
        self.start_button.pack(side='left')
        self.stop_button = ttk.Button(top, text='停止', state='disabled', command=self.stop_receive)
        self.stop_button.pack(side='left', padx=(8, 0))
        ttk.Label(outer, textvariable=self.status, wraplength=940).pack(anchor='w', pady=(12, 8))
        self.canvas = tk.Canvas(outer, bg='#111111', highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)
        self.canvas.create_text(430, 200, text='PS2映像プレビュー', fill='#aaaaaa', font=('Yu Gothic UI', 18))
        ttk.Label(outer, textvariable=self.counts, font=('Yu Gothic UI', 12)).pack(anchor='w', pady=(10, 6))
        self.bar = ttk.Progressbar(outer, maximum=100, mode='determinate')
        self.bar.pack(fill='x')
        byte_panel = ttk.LabelFrame(outer, text='受信バイト', padding=8)
        byte_panel.pack(fill='x', pady=(8, 0))
        ttk.Label(byte_panel, textvariable=self.byte_counts).pack(anchor='w')
        ttk.Label(byte_panel, textvariable=self.byte_range, wraplength=920).pack(anchor='w', pady=(3, 4))
        ttk.Label(byte_panel, textvariable=self.hex_preview, font=('Consolas', 10)).pack(anchor='w')
        ttk.Label(outer, textvariable=self.details, wraplength=940).pack(anchor='w', pady=(6, 8))
        bottom = ttk.Frame(outer)
        bottom.pack(fill='x')
        ttk.Label(bottom, text='保存先').pack(side='left', padx=(0, 8))
        self.destination = ttk.Entry(bottom, textvariable=self.output_dir)
        self.destination.pack(side='left', fill='x', expand=True)
        self.browse_button = ttk.Button(bottom, text='変更', command=self.browse)
        self.browse_button.pack(side='left', padx=(8, 0))
        ttk.Label(outer, text='正常なフレームは随時保存。欠落は次の周回で補完し、全体CRC一致後に完成ファイルを保存します。',
                  wraplength=940).pack(anchor='w', pady=(8, 0))
        self.refresh()
        root.after(75, self.poll)
        if args.video or args.images or args.camera is not None:
            root.after(250, self.start)

    def refresh(self):
        try:
            self.device_list = devices()
        except Exception as error:
            self.status.set(f'機器一覧を取得できません: {error}')
            self.device_list = [(i, f'カメラ {i}') for i in range(5)]
        self.device['values'] = [f'{i}: {name}' for i, name in self.device_list]
        selected = next((j for j, (_, name) in enumerate(self.device_list)
                         if 'UGREEN' in name or 'Monster' in name), 0)
        if self.args.camera is not None:
            selected = next((j for j, (index, _) in enumerate(self.device_list)
                             if index == self.args.camera), selected)
        if self.device_list:
            self.device.current(selected)

    def browse(self):
        path = filedialog.askdirectory(initialdir=self.output_dir.get())
        if path:
            self.output_dir.set(path)

    def start(self):
        if self.worker is not None and self.worker.is_alive():
            return
        if not self.args.video and not self.args.images and self.device.current() < 0:
            messagebox.showerror('機器を選択', 'キャプチャ機器を選んでください。')
            return
        directory = self.output_dir.get().strip()
        if not directory:
            messagebox.showerror('保存先', '保存先を指定してください。')
            return
        source = self.device_list[self.device.current()][0] if self.device.current() >= 0 else 0
        self.stop.clear()
        self.preview = None
        self.output_file = None
        self.bar['value'] = 0
        self.counts.set('受信 0 / —　　欠落 —　　CRCエラー 0')
        self.byte_counts.set('受信済み 0 bytes')
        self.byte_range.set('直近の受信範囲 —　　先頭の欠落位置 —')
        self.hex_preview.set('CRC合格フレームの先頭32 bytesをここに表示します。')
        self.status.set('キャプチャ機器を開いています…')
        for control in (self.start_button, self.refresh_button, self.browse_button, self.destination):
            control['state'] = 'disabled'
        self.device['state'] = 'disabled'
        self.stop_button['state'] = 'normal'
        self.worker = threading.Thread(target=self.receive, args=(source, directory), daemon=True)
        self.worker.start()

    def receive(self, source, directory):
        stream = None
        try:
            stream = (png_frames(self.args.images) if self.args.images else
                      video_frames(self.args.video if self.args.video else source,
                                   'auto' if self.args.video else 'dshow'))
            transfer = Transfer(directory)
            errors = Counter()
            last_decode = last_status = 0.0
            for image in stream:
                if self.stop.is_set():
                    break
                self.preview = image
                now = time.monotonic()
                if now - last_decode < .07 and not self.args.images:
                    continue
                last_decode = now
                decode_frame = image
                if image.shape[1] > 960:
                    decode_frame = cv2.resize(image, (960, round(image.shape[0]*960/image.shape[1])),
                                              interpolation=cv2.INTER_AREA)
                try:
                    frame = decode_image(decode_frame)
                except DecodeError as error:
                    errors[str(error)] += 1
                else:
                    # Session/storage errors are actionable, not bad video frames.
                    if transfer.store is not None and transfer.store.identity != frame.identity:
                        transfer = Transfer(directory)
                        self.events.put(('status', '密度または送信sessionが変わりました。別の受信セットを開始します。'))
                    progress = transfer.accept(frame)
                    if progress.complete:
                        self.events.put(('complete', progress))
                        break
                if now - last_status > .25:
                    self.events.put(('progress', (transfer.progress(), dict(errors))))
                    last_status = now
            else:
                if self.args.video or self.args.images:
                    self.events.put(('status', '入力終了。未受信フレームは保存先のcheckpointから再開できます。'))
                else:
                    raise OSError('キャプチャから映像を取得できません。OBS側の同じキャプチャソースを無効にして再試行してください。')
            if self.stop.is_set():
                self.events.put(('status', '停止しました。受信済みフレームは保存済みです。'))
        except Exception as error:
            self.events.put(('error', str(error)))
        finally:
            if stream is not None:
                stream.close()
            self.events.put(('done', None))

    def stop_receive(self):
        self.stop.set()
        self.stop_button['state'] = 'disabled'
        self.status.set('停止しています…')

    def show_bytes(self, progress):
        percent = progress.received_bytes*100/progress.source_size if progress.source_size else 0
        self.byte_counts.set(f'受信済み {progress.received_bytes:,} / {progress.source_size:,} bytes'
                             f'（{percent:.1f}%）　未受信 {progress.source_size-progress.received_bytes:,} bytes')
        if progress.last_offset is None:
            return
        start, length = progress.last_offset, progress.last_length
        end = start + max(0, length-1)
        missing = f'0x{progress.first_missing_offset:08X}' if progress.first_missing_offset is not None else 'なし'
        state = '新規取得' if progress.last_was_new else '取得済みの再受信'
        self.byte_range.set(f'直近 0x{start:08X} ～ 0x{end:08X}（{length} bytes、{state}）'
                            f'　先頭の欠落 {missing}')
        symbols = progress.last_hex.split()
        rows = [f'{start+i:08X}  ' + ' '.join(symbols[i:i+16]) for i in range(0, len(symbols), 16)]
        self.hex_preview.set('\n'.join(rows) if rows else 'ペイロードなし')

    def poll(self):
        while True:
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == 'progress':
                progress, errors = value
                self.show_bytes(progress)
                if self.args.report:
                    import json
                    from dataclasses import asdict
                    Path(self.args.report).write_text(json.dumps({**asdict(progress), 'errors': errors}, indent=2), encoding='utf-8')
                crc_errors = errors.get('frame CRC', 0)
                total = progress.total or '—'
                missing = progress.total-progress.received if progress.total else '—'
                self.counts.set(f'受信 {progress.received} / {total}　　欠落 {missing}　　CRCエラー {crc_errors}')
                if progress.total:
                    self.bar['value'] = progress.received*100/progress.total
                    label = '固定テストデータ' if progress.object_type == 0 else 'ROM0'
                    self.status.set(f'{label}を受信中。欠落フレームを周回から補完しています。')
                    cols, rows, _ = GRIDS[progress.profile]
                    self.details.set(f'{progress.source_size:,} bytes　送信元CRC32 {progress.source_crc:08X}'
                                     f'　グリッド {cols}×{rows}')
                else:
                    self.status.set('映像取得中。PS2Vの四隅マーカーと正常なフレームを待っています。')
            elif kind == 'complete':
                self.show_bytes(value)
                self.bar['value'] = 100
                self.counts.set(f'受信 {value.total} / {value.total}　　欠落 0　　全体CRC一致')
                self.output_file = value.output
                suffix = ' 固定テストデータとも完全一致しました。' if value.test_matches else ''
                self.status.set('受信完了。全体CRCを確認して保存しました。' + suffix)
                self.details.set(value.output)
                if self.args.report:
                    import json
                    from dataclasses import asdict
                    Path(self.args.report).write_text(json.dumps(asdict(value), indent=2), encoding='utf-8')
            elif kind in ('status', 'error'):
                self.status.set(value)
                if kind == 'error' and self.args.report:
                    import json
                    Path(self.args.report).write_text(json.dumps({'complete': False, 'error': value}), encoding='utf-8')
            elif kind == 'done':
                for control in (self.start_button, self.refresh_button, self.browse_button, self.destination):
                    control['state'] = 'normal'
                self.device['state'] = 'readonly'
                self.stop_button['state'] = 'disabled'
        if self.preview is not None:
            image, self.preview = self.preview, None
            picture = Image.fromarray(image)
            picture.thumbnail((max(100, self.canvas.winfo_width()), max(100, self.canvas.winfo_height())))
            self.image_ref = ImageTk.PhotoImage(picture)
            self.canvas.delete('all')
            self.canvas.create_image(self.canvas.winfo_width()/2, self.canvas.winfo_height()/2,
                                     image=self.image_ref, anchor='center')
        if self.args.auto_exit and self.worker is not None and not self.worker.is_alive() and self.events.empty():
            self.root.destroy()
            return
        self.root.after(75, self.poll)

    def close(self):
        self.stop.set()
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser(description='Native PS2V capture receiver')
    source = parser.add_mutually_exclusive_group()
    source.add_argument('--video', help='optional prerecorded video')
    source.add_argument('--images', help='optional reference PNG directory')
    source.add_argument('--camera', type=int, help='start receiving from this device index')
    parser.add_argument('--output-dir', default=str(Path(__file__).resolve().parents[1] / 'captures'))
    parser.add_argument('--auto-exit', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--report', help=argparse.SUPPRESS)
    args = parser.parse_args()
    root = tk.Tk()
    App(root, args)
    root.mainloop()


if __name__ == '__main__':
    main()
