import pyxel as px
import os
import json
import sounds
from bdf import BDFRenderer

LOCAL = False
try:
    from js import Blob, URL, document
except:
    LOCAL = True

# カラー定義
COL_BACK_PRIMARY = 7
COL_BACK_SECONDARY = 12
COL_BTN_BASIC = 5
COL_BTN_SELECTED = 6
COL_TEXT_BASIC = 1
COL_TEXT_MUTED = 5
COL_SHADOW = 0

# 生成する曲の小節数（8固定）
BARS_NUMBERS = 8

# パラメータ指定用
list_tones = [
    (11, "Pulse solid"),
    (8, "Pulse thin"),
    (2, "Pulse soft"),
    (10, "Square solid"),
    (6, "Square thin (Harp)"),
    (4, "Square soft (Flute)"),
]
list_melo_lowest_note = [
    (28, "E2"),
    (29, "F2"),
    (30, "F#2"),
    (31, "G2"),
    (32, "G#2"),
    (33, "A2"),
    (34, "A#2"),
]
list_melo_length_rate = [
    (0.4, 1.0, "4/8"),
    (0.2, 0.6, "4/8/16"),
    (0.4, 0.4, "4/16"),
    (0.0, 0.4, "8/16"),
    (0.0, 0.0, "16"),
]


# 部品
class Element:
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def mouse_in(self):
        mx = px.mouse_x
        my = px.mouse_y
        return (
            mx >= self.x
            and mx < self.x + self.w
            and my >= self.y
            and my < self.y + self.h
        )


# タブ
class Tab(Element):
    def __init__(self, idx, x, y, text):
        super().__init__(x, y, 64, 12)
        self.idx = idx
        self.text = text

    def draw(self, app):
        active = self.idx == app.tab
        rect_c = COL_BACK_PRIMARY if active else COL_BACK_SECONDARY
        text_c = COL_TEXT_BASIC if active else COL_TEXT_MUTED
        px.rect(self.x, self.y, self.w, self.h, rect_c)
        text_info = app.get_text(self.text)
        x = int(self.x + self.w / 2 - text_info[1])
        y = int(self.y + self.h / 2 - 4)
        app.text(x, y, self.text, text_c)


# アイコン
class Icon(Element):
    def __init__(self, id, x, y):
        super().__init__(x, y, 16, 12)
        self.id = id
        self.state = 0

    def draw(self, app):
        state = 0
        if self.id == 0:
            state = 1 if px.play_pos(0) else 0
        elif self.id == 1:
            state = 1 if not px.play_pos(0) else 0
        elif self.id == 2:
            state = 1 if app.loop else 0
        elif self.id == 3:
            state = 1 if app.show_export else 0
        px.blt(self.x, self.y, 0, self.id * 16, state * 16, self.w, self.h, 0)
        self.state = state


# ボタン
class Button(Element):
    def __init__(self, tab, type, key, x, y, w, text):
        super().__init__(x, y, w, 10)
        self.tab = tab
        self.type = type
        self.key = key
        self.x = x
        self.y = y
        self.w = w
        self.text = text
        self.selected = False

    def draw(self, app):
        if not self.visible(app):
            return
        text_s = str(self.text)
        if app.parm[self.type] == self.key:
            rect_c = COL_BTN_SELECTED
        else:
            rect_c = COL_BTN_BASIC
        text_c = COL_TEXT_BASIC
        px.rect(self.x, self.y, self.w - 1, self.h - 1, rect_c)
        px.text(
            self.x + self.w / 2 - len(text_s) * 2,
            self.y + self.h / 2 - 3,
            text_s,
            text_c,
        )

    def visible(self, app):
        return self.tab is None or app.tab == self.tab


# アプリ
class App:
    def __init__(self):
        self.output_file = "music.json"
        px.init(256, 256, title="8bit BGM generator", quit_key=px.KEY_NONE)
        px.load("assets.pyxres")
        self.bdf = BDFRenderer("misaki_gothic.bdf")
        self.parm = {
            "preset": 0,
            "transpose": 0,
            "language": 1,
            "melo_jutout_rate": 0.4,  # 音符の半ずらし発生率
            "base_highest_note": 26,  # ベース（ルート）最高音
        }
        self.loop = True
        with open("tones.json", "rt", encoding="utf-8") as fin:
            self.tones = json.loads(fin.read())
        with open("patterns.json", "rt", encoding="utf-8") as fin:
            self.patterns = json.loads(fin.read())
        with open("generator.json", "rt", encoding="utf-8") as fin:
            self.generator = json.loads(fin.read())
        # タブ、共通ボタン、アイコン
        self.tabs = []
        self.buttons = []
        self.icons = []
        list_tab = (0, 1, 2)
        list_language = ("Japanese", "English")
        for i, elm in enumerate(list_tab):
            self.set_tab(i, i * 64 + 4, 20, elm)
        for i in range(4):
            self.set_icon(i, 4 + i * 20, 4)
        for i, elm in enumerate(list_language):
            self.set_btn(None, "language", i, 116 + 48 * i, 6, 48, elm)
        # 基本タブ
        for i, elm in enumerate(self.generator["preset"]):
            self.set_btn(0, "preset", i, 8 + 24 * i, 50, 24, i + 1)
        for i in range(12):
            key = (i + 6) % 12 - 11
            self.set_btn(0, "transpose", key, 8 + 20 * i, 114, 20, i - 5)
        # コードとリズムタブ
        list_speed = [360, 312, 276, 240, 216, 192, 168, 156]
        list_base_quantize = [12, 13, 14, 15]
        for i, elm in enumerate(list_speed):
            self.set_btn(1, "speed", elm, 8 + 24 * i, 50, 24, int(28800 / elm))
        for i, elm in enumerate(self.generator["chords"]):
            self.set_btn(1, "chord", i, 8 + 24 * i, 80, 24, i + 1)
        for i, elm in enumerate(self.generator["base"]):
            self.set_btn(1, "base", i, 8 + 24 * i, 110, 24, i + 1)
        for i, elm in enumerate(list_base_quantize):
            quantize = str(int(elm * 100 / 16)) + "%"
            self.set_btn(1, "base_quantize", elm, 8 + 24 * i, 140, 24, quantize)
        for i, elm in enumerate(self.generator["drums"]):
            self.set_btn(1, "drums", i, 8 + 24 * i, 170, 24, i + 1)
        self.set_btn(1, "drums", -1, 8 + 24 * 8, 170, 48, "No Drums")
        # メロディータブ
        list_melo_continue_rate = [0.0, 0.2, 0.4, 0.6]
        list_melo_rest_rate = [0.0, 0.1, 0.2, 0.3, 0.4]
        for i, elm in enumerate(list_tones):
            self.set_btn(2, "melo_tone", i, 8 + 24 * i, 50, 24, i + 1)
        for i, elm in enumerate(list_melo_lowest_note):
            self.set_btn(2, "melo_lowest_note", elm[0], 8 + 24 * i, 80, 24, elm[1])
        for i, elm in enumerate(list_melo_length_rate):
            self.set_btn(2, "melo_length_rate", i, 8 + 32 * i, 110, 32, elm[2])
        for i, elm in enumerate(list_melo_rest_rate):
            self.set_btn(2, "melo_rest_rate", elm, 8 + 24 * i, 166, 24, elm)
        for i, elm in enumerate(list_melo_continue_rate):
            self.set_btn(2, "melo_continue_rate", elm, 8 + 24 * i, 196, 24, elm)
        self.items = []
        self.set_preset(self.parm["preset"])
        self.play()
        self.saved_playkey = [-1, -1]
        self.show_export = None
        self.tab = 0
        px.mouse(True)
        px.run(self.update, self.draw)

    @property
    def total_len(self):
        return BARS_NUMBERS * 16

    def set_tab(self, *args):
        self.tabs.append(Tab(*args))

    def set_icon(self, *args):
        self.icons.append(Icon(*args))

    def set_btn(self, *args):
        self.buttons.append(Button(*args))

    def update(self):
        if not px.btnp(px.MOUSE_BUTTON_LEFT):
            return
        if self.show_export:
            self.show_export = None
            return
        for tab in self.tabs:
            if tab.mouse_in():
                self.tab = tab.idx
        for icon in self.icons:
            if icon.mouse_in():
                if icon.id == 0 and icon.state == 0:
                    self.play()
                elif icon.id == 1 and icon.state == 0:
                    px.stop()
                elif icon.id == 2:
                    self.loop = not self.loop
                    if px.play_pos(0):
                        self.play()
                elif icon.id == 3:
                    if LOCAL:
                        with open(os.path.abspath(self.output_file), "wt") as fout:
                            fout.write(json.dumps(self.music))
                    else:
                        blob = Blob.new(self.music, {"type": "text/plain"})
                        blob_url = URL.createObjectURL(blob)
                        a = document.createElement("a")
                        a.href = blob_url
                        a.download = self.output_file
                        document.body.appendChild(a)
                        a.click()
                        document.body.removeChild(a)
                        URL.revokeObjectURL(blob_url)
                    self.show_export = True
        for button in self.buttons:
            if button.visible(self) and button.mouse_in():
                self.parm[button.type] = button.key
                if button.type == "language":
                    return
                if button.type == "preset":
                    self.set_preset(button.key)
                else:
                    make_melody = button.type in [
                        "transpose",
                        "chord",
                        "melo_lowest_note",
                        "melo_length_rate",
                        "melo_continue_rate",
                        "melo_rest_rate",
                    ]
                    self.generate_music(make_melody)
                self.play()

    def draw(self):
        px.cls(COL_BACK_SECONDARY)
        px.rect(4, 32, 248, 184, COL_BACK_PRIMARY)
        px.text(220, 8, "ver 1.02", COL_TEXT_MUTED)
        if self.tab == 0:
            self.text(8, 40, 3, COL_TEXT_BASIC)
            px.rectb(8, 64, 240, 32, COL_TEXT_MUTED)
            self.text(16, 68, 4, COL_TEXT_MUTED)
            self.text(16, 76, 5, COL_TEXT_MUTED)
            self.text(16, 84, 6, COL_TEXT_MUTED)
            self.text(8, 104, 7, COL_TEXT_BASIC)
        elif self.tab == 1:
            self.text(8, 40, 9, COL_TEXT_BASIC)
            self.text(8, 70, 10, COL_TEXT_BASIC)
            chord_name = self.generator["chords"][self.parm["chord"]]["description"]
            self.text(80, 70, chord_name, COL_TEXT_MUTED)
            self.text(8, 100, 11, COL_TEXT_BASIC)
            self.text(8, 130, 12, COL_TEXT_BASIC)
            self.text(8, 160, 13, COL_TEXT_BASIC)
            px.rectb(8, 184, 240, 24, COL_TEXT_MUTED)
            self.text(16, 188, 14, COL_TEXT_MUTED)
            self.text(16, 196, 15, COL_TEXT_MUTED)
        elif self.tab == 2:
            self.text(8, 40, 16, COL_TEXT_BASIC)
            melo_tone_name = list_tones[self.parm["melo_tone"]][1]
            self.text(40, 40, melo_tone_name, COL_TEXT_MUTED)
            self.text(8, 70, 17, COL_TEXT_BASIC)
            self.text(8, 100, 18, COL_TEXT_BASIC)
            px.rectb(8, 124, 240, 24, COL_TEXT_MUTED)
            self.text(16, 128, 19, COL_TEXT_MUTED)
            self.text(16, 136, 20, COL_TEXT_MUTED)
            self.text(8, 156, 21, COL_TEXT_BASIC)
            self.text(8, 186, 22, COL_TEXT_BASIC)
        # タブ、ボタン、モーダル
        for tab in self.tabs:
            tab.draw(self)
        for button in self.buttons:
            button.draw(self)
        for icon in self.icons:
            icon.draw(self)
        if self.show_export:
            h = 12 * 5 + 18
            y = 72
            px.rect(20, y + 4, 224, h, COL_SHADOW)
            px.rect(16, y, 224, h, COL_BTN_SELECTED)
            px.rectb(16, y, 224, h, COL_BTN_BASIC)
            for i in range(5):
                self.text(20, y + 4 + 12 * i, 24 + i, COL_TEXT_BASIC)
        # 鍵盤
        sx = 8
        sy = 232
        px.rect(sx, sy, 5 * 42 - 1, 16, 7)
        for x in range(5 * 7 - 1):
            px.line(sx + 5 + x * 6, sy, sx + 5 + x * 6, sy + 15, 0)
        for o in range(5):
            px.rect(sx + 3 + o * 42, sy, 5, 9, 0)
            px.rect(sx + 9 + o * 42, sy, 5, 9, 0)
            px.rect(sx + 21 + o * 42, sy, 5, 9, 0)
            px.rect(sx + 27 + o * 42, sy, 5, 9, 0)
            px.rect(sx + 33 + o * 42, sy, 5, 9, 0)
        (x1, _) = self.get_piano_xy(self.parm["melo_lowest_note"])
        (x2, _) = self.get_piano_xy(self.parm["melo_lowest_note"] + 16)
        px.rect(x1, 229, x2 - x1 + 3, 2, 11)
        (x1, _) = self.get_piano_xy(self.parm["base_highest_note"] - 24)
        (x2, _) = self.get_piano_xy(self.parm["base_highest_note"])
        px.rect(x1, 229, x2 - x1 + 3, 2, 10)
        # 音域バー
        if px.play_pos(0):
            pos = px.play_pos(0)[1]
            ticks = self.parm["speed"] / 16
            loc = int(pos // ticks)
            bars = loc // 16 + 1
            beats = (loc // 4) % 4 + 1
        else:
            return
        # 再生インジケータ
        px.text(8, 220, f"bars: {bars}/{BARS_NUMBERS}", COL_TEXT_BASIC)
        px.text(56, 220, f"beats: {beats}/{4}", COL_TEXT_BASIC)
        item = self.items[loc]
        # 演奏情報
        self.draw_playkey(0, item[6], 11)
        self.draw_playkey(1, item[10], 10)
        for i, elm in enumerate(self.patterns):
            y = i // 3
            x = i % 3
            c = COL_TEXT_BASIC if item[14] == elm["key"] else COL_TEXT_MUTED
            px.text(220 + x * 10, 233 + y * 8, elm["abbr"], c)

    def draw_playkey(self, key, input, c):
        value = input
        if value is None:
            value = self.saved_playkey[key]
        else:
            self.saved_playkey[key] = value
        if value < 0:
            return
        (x, y) = self.get_piano_xy(value)
        px.rect(x, y, 3, 4, c)

    def get_piano_xy(self, value):
        note12 = value % 12
        oct = value // 12
        x = 8 + (1, 4, 7, 10, 13, 19, 22, 25, 28, 31, 34, 37)[note12] + oct * 42
        y = 232 + (2 if note12 in [1, 3, 6, 8, 10] else 10)
        return x, y

    def play(self):
        for ch, sound in enumerate(self.music):
            px.sound(ch).set(*sound)
            px.play(ch, ch, loop=self.loop)

    def set_preset(self, value):
        preset = self.generator["preset"][value]
        for key in preset:
            self.parm[key] = preset[key]
        self.generate_music()

    def text(self, x, y, value, c):
        if type(value) is int:
            self.bdf.text(x, y, self.get_text(value)[0], c)
        else:
            self.bdf.text(x, y, value, c)

    def get_text(self, value):
        list_text = [
            ("きほん", "Basic"),
            ("コードとリズム", "Chord & Rhythm"),
            ("メロディ", "Melody"),
            ("プリセット", "Preset"),
            (
                "「コードとリズム」「メロディ」の　オススメせっていを",
                "The recommended settings for 'Chord and Rhyth' and",
            ),
            (
                "とうろくしてあります。　はじめてのかたは",
                "'Melody' are registered. If you are a first time user,",
            ),
            ("プリセットをもとに　きょくをつくってみましょう。", "create a song based on the presets."),
            ("トランスポーズ", "Transpose"),
            ("", ""),
            ("テンポ", "Tempo"),
            ("コードしんこう", "Chord Progression"),
            ("ベース　パターン", "Bass Patterns"),
            ("ベース　クオンタイズ", "Base Quantize"),
            ("ドラム　パターン", "Drums Patterns"),
            ("「No drums」をせんたくすると　ドラムパートのかわりに", "When 'No drums' is selected, "),
            (
                "メロディにリバーブがかかります。",
                "reverb is applied to the melody instead of the drum part.",
            ),
            ("ねいろ", "Tone"),
            ("おとのたかさ（さいていおん）", "Sound Height (lowest note)"),
            ("おんぷのながさ", "Notes Length"),
            (
                "どのながさの おんぷをつかうか けっていします。",
                "Determines which length of notes to use.",
            ),
            (
                "「４／８」なら ４ぶおんぷと８ぶおんぷを　つかいます。",
                "ex) '4/8' uses quarter notes and eighth notes.",
            ),
            ("きゅうふのひんど", "Rests Ratio"),
            ("じぞくおんのひんど", "Sustained Tone Ratio"),
            ("", ""),
            ("【ローカルでうごかしているばあい】", "[When running in a local environment]"),
            (
                "　プログラムのフォルダの music.json にほぞんしました。",
                "  Saved in 'music.json' in the program folder.",
            ),
            ("", ""),
            ("【ブラウザでうごかしているばあい】", "[When running in a browser]"),
            (
                "　music.json がダウンロードされます。",
                " 'music.json' will be downloaded.",
            ),
        ]
        lang = self.parm["language"]
        text = list_text[value][lang]
        width = 4 if lang == 0 else 2
        return text, len(text) * width

    def generate_music(self, make_melody=True):
        px.stop()
        parm = self.parm
        no_drum = parm["drums"] < 0
        base = self.generator["base"][parm["base"]]
        drums = self.generator["drums"][parm["drums"]]
        chord = self.generator["chords"][parm["chord"]]
        # コードリスト準備
        self.chord_lists = []
        for progression in chord["progression"]:
            chord_list = {
                "loc": progression["loc"],
                "base": 0,
                "notes": [],
                "no_root": False,
                "repeat": progression["repeat"] if "repeat" in progression else None,
            }
            if "repeat" in progression:
                chord_list["base"] = self.chord_lists[progression["repeat"]]["base"]
            if "notes" in progression:
                notes = progression["notes"]
                note_chord_cnt = 0
                # ベース音設定
                for idx in range(12):
                    if notes[idx] == 2:
                        chord_list["base"] = idx
                    if notes[idx] in [1, 2, 3]:
                        note_chord_cnt += 1
                chord_list["no_root"] = note_chord_cnt > 3
                # レンジを決める
                note_highest = None
                idx = 0
                while True:
                    note_type = notes[idx % 12]
                    note = 12 + idx + parm["transpose"]
                    if note >= parm["melo_lowest_note"]:
                        if note_type in [1, 2, 3]:
                            chord_list["notes"].append((note, note_type))
                            if note_highest is None:
                                note_highest = note + 12
                        elif note_type == 9 and note_highest:
                            chord_list["notes"].append((note, note_type))
                    if note_highest and note >= note_highest:
                        break
                    idx += 1
            self.chord_lists.append(chord_list)
        # バッキング生成
        items = []
        for loc in range(self.total_len):
            items.append([None for _ in range(19)])
            (chord_idx, _) = self.get_chord(loc)
            chord_list = self.chord_lists[chord_idx]
            item = items[loc]
            tick = loc % 16  # 拍(0-15)
            if loc == 0:  # 最初の行（セットアップ）
                item[0] = parm["speed"]  # テンポ
                item[1] = 48  # 4/4拍子
                item[2] = 3  # 16分音符
                item[3] = list_tones[parm["melo_tone"]][0]  # メロディ音色
                item[4] = 5  # メロディ音量
                item[5] = 14  # メロディ音長
                item[7] = 7  # ベース音色
                item[8] = 7  # ベース音量
                item[9] = parm["base_quantize"]  # ベース音長
                if no_drum:
                    item[11] = item[3]  # リバーブ音色
                    item[12] = 2  # リバーブ音量
                    item[13] = item[5]
                else:
                    item[12] = 5  # ドラム音量
            # ベース音設定
            pattern = "basic" if loc // 16 < 7 else "final"
            base_note = base[pattern][tick]
            if not base_note is None and base_note >= 0:
                highest = parm["base_highest_note"]
                pattern = "basic" if loc // 16 < 7 else "final"
                base_root = 12 + parm["transpose"] + chord_list["base"]
                while base_root + 24 > highest:
                    base_root -= 12
                base_note = base_root + base_note
            item[10] = base_note
            # ドラム音設定
            if not no_drum:
                pattern = "basic" if (loc // 16) % 4 < 3 else "final"
                item[14] = drums[pattern][tick] if drums[pattern][tick] else None
        # メロディー生成
        while make_melody:
            self.generate_melody()
            if self.check_melody():
                break
        # フォーマットにメロディとリバーブを設定
        for loc in range(self.total_len):
            item = items[loc]
            item[6] = self.melody_notes[loc]
            if no_drum:
                item[14] = self.melody_notes[
                    (loc + self.total_len - 1) % self.total_len
                ]
        # 完了処理
        self.music = sounds.compile(items, self.tones, self.patterns)
        self.items = items

    # メロディ生成
    def generate_melody(self):
        parm = self.parm
        cur_chord_idx = -1  # 現在のコード（self.chord_listsのインデックス）
        cur_chord_loc = -1  # 現在のコードの開始位置
        chord_list = []
        is_repeat = False  # リピートモード
        self.note_continue_count = 0  # 音符の連続個数（休符が入るとリセット）
        self.prev_note = -1  # 直前のメロディー音
        self.first_note = True  # コード切り替え後の最初のノート
        self.melody_notes = [-2 for _ in range(self.total_len)]
        for loc in range(self.total_len):
            # すでに埋まっていたらスキップ
            if self.melody_notes[loc] != -2:
                continue
            # 生成する音符の長さを取得
            note_len = self.get_note_len(loc)
            # コード切替判定
            change_code = False
            premonitory = False
            (next_chord_idx, next_chord_loc) = self.get_chord(loc)
            if next_chord_idx > cur_chord_idx:
                change_code = True
            elif not is_repeat and loc + note_len > next_chord_loc:
                (next_chord_idx, next_chord_loc) = self.get_chord(loc + note_len)
                change_code = True
                premonitory = True
                print(loc, note_len, "先取音発生")
            if change_code:
                chord_list = self.chord_lists[next_chord_idx]
                cur_chord_idx = next_chord_idx
                cur_chord_loc = loc
                self.first_note = True
                is_repeat = not chord_list["repeat"] is None
            # 小節単位の繰り返し
            if is_repeat:
                repeat_loc = self.chord_lists[chord_list["repeat"]]["loc"]
                repeat_note = self.melody_notes[repeat_loc + loc - cur_chord_loc]
                self.put_melody(loc, repeat_note)
                continue
            # 直前のメロディーのインデックスを今のコードリストと照合(構成音から外れていたらNone)
            cur_idx = None
            if not premonitory:
                for idx, note in enumerate(chord_list["notes"]):
                    if self.prev_note == note[0]:
                        cur_idx = idx
                        break
            # 休符（休符の後の音符が2個未満のときはスキップ）
            if (
                px.rndf(0.0, 1.0) < parm["melo_rest_rate"]
                and self.note_continue_count > 1
            ):
                self.put_melody(loc, -1, note_len)
                print(loc, "休符")
                continue
            # 初音（直前が休符 or コード構成音から外れた場合は、コード構成音を取得）
            if self.prev_note < 0 or cur_idx is None:
                idx = self.get_target_note(chord_list, self.first_note)
                note = chord_list["notes"][idx][0]
                self.put_melody(loc, note, note_len)
                print(loc, "初音")
                continue
            # 長音（割合判定）
            if px.rndf(0.0, 1.0) < parm["melo_continue_rate"]:
                self.put_melody(loc, None, note_len)
                print(loc, "長音")
                continue
            # 各種変数準備
            next_idx = self.get_target_note(chord_list)
            diff = abs(next_idx - cur_idx)
            direction = 1 if next_idx > cur_idx else -1
            left_space = (next_chord_loc - loc) // note_len  # 小節内にあと何個音符を置けるか
            # 刺繍音/同音
            if diff == 0:
                cnt = px.rndi(0, 2)
                if cnt and left_space >= cnt * 2:
                    for i in range(cnt):
                        while next_idx == cur_idx:
                            next_idx = self.get_target_note(chord_list)
                        direction = 1 if next_idx > cur_idx else -1
                        note = chord_list["notes"][cur_idx + direction][0]
                        prev_note = self.prev_note
                        self.put_melody(loc + i * 2 * note_len, note, note_len)
                        self.put_melody(
                            loc + (i * 2 + 1) * note_len, prev_note, note_len
                        )
                    print(loc, "刺繍音")
                    continue
                else:
                    self.put_melody(loc, self.prev_note, note_len)
                    print(loc, "同音")
                    continue
            # ステップに必要な長さが足りない/跳躍量が大きい/割合で跳躍音採用
            jump_rate = 0  # parm["melo_rest_rate"] / 2 + 0.1  # 跳躍音採用率
            if (
                loc + diff * note_len >= next_chord_loc
                or diff > 12
                or px.rndf(0.0, 1.0) < jump_rate
            ):
                note = chord_list["notes"][next_idx][0]
                self.put_melody(loc, note, note_len)
                print(loc, "跳躍")
                continue
            # ステップ
            cur_loc = loc
            print(loc, "ステップ", note_len)
            while next_idx != cur_idx:
                cur_idx += direction
                note = chord_list["notes"][cur_idx][0]
                self.put_melody(cur_loc, note, note_len)
                cur_loc += note_len

    # メロディ検査（コード中の重要構成音が入っているか）
    def check_melody(self):
        cur_chord_idx = -1
        need_notes_list = []
        for loc in range(self.total_len):
            (next_chord_idx, _) = self.get_chord(loc)
            if next_chord_idx > cur_chord_idx:
                # need_notes_listが残っている＝重要構成音が満たされていない
                if len(need_notes_list) > 0:
                    return False
                cur_chord_idx = next_chord_idx
                chord_list = self.chord_lists[cur_chord_idx]["notes"]
                need_notes_list = []
                for chord in chord_list:
                    note = chord[0] % 12
                    if chord[1] == 1 and not note in need_notes_list:
                        need_notes_list.append(note)
            note = self.melody_notes[loc]
            if not note is None and note >= 0 and note % 12 in need_notes_list:
                need_notes_list.remove(note % 12)
        return True

    # コードリスト取得（locがchords_listsの何番目のコードか、次のコードの開始位置を返す）
    def get_chord(self, loc):
        chord_lists_cnt = len(self.chord_lists)
        next_chord_loc = 16 * BARS_NUMBERS
        for rev_idx in range(chord_lists_cnt):
            idx = chord_lists_cnt - rev_idx - 1
            if loc >= self.chord_lists[idx]["loc"]:
                break
            else:
                next_chord_loc = self.chord_lists[idx]["loc"]
        return idx, next_chord_loc

    # 生成する音符の長さを決める
    def get_note_len(self, loc):
        parm = self.parm
        seed = px.rndf(0.0, 1.0)
        beat = loc % 4
        if (
            seed <= list_melo_length_rate[parm["melo_length_rate"]][0]
            and loc + 3 < self.total_len
            and (beat in [0, 2])
            and (beat == 0 or px.rndf(0.0, 1.0) < parm["melo_jutout_rate"])
        ):
            return 4
        elif (
            seed <= list_melo_length_rate[parm["melo_length_rate"]][1]
            and loc + 1 < self.total_len
            and (beat in [0, 2] or px.rndf(0.0, 1.0) < parm["melo_jutout_rate"])
        ):
            return 2
        return 1

    # 跳躍音の跳躍先を決定
    def get_target_note(self, chord_list, force_no_root=False):
        no_root = force_no_root or chord_list["no_root"]
        notes = chord_list["notes"]
        while True:
            idx = px.rndi(0, len(notes) - 1)
            allowed_types = [1, 3] if no_root else [1, 2, 3]
            if not notes[idx][1] in allowed_types:
                continue
            note = notes[idx][0]
            if self.prev_note >= 0:
                diff = abs(self.prev_note - note)
                if diff > 8 and diff != 12:
                    continue
            return idx

    # メロディのトーンを配置
    def put_melody(self, loc, note, note_len=1):
        for idx in range(note_len):
            self.melody_notes[loc + idx] = note if idx == 0 else None
        if note is not None:
            if note < 0:
                self.note_continue_count = 0
            else:
                self.note_continue_count += 1
            self.prev_note = note
            self.first_note = False


App()
