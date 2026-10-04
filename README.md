# soundtrack — Soundtrack as code

用几行 JSON 谱写配乐，输出 wav。**零第三方依赖**，Python 3.7 起能跑，iPhone 上也能跑。

```bash
$ python -m soundtrack render examples/ui-fx.json -o ui.wav
ui-fx  100 BPM  22050 Hz  6 轨
写入 ui.wav  (340 KB / 7.9 秒)  用时 0.5s
```

它不做什么宏大的事：给你一个文本格式的曲子，按时间轴合成出 PCM，写成 wav。
游戏要点击音、教育视频要章节音、独立开发者要一段能跑进 git 的 BGM——都够用。

---

## 为什么是纯标准库

因为要能在手机上跑。numpy / scipy 在 iOS 的 Python 环境里装不上（或者装完体积比用途还大），
而这个库真的只需要 `math.sin`、`array` 和 `wave`。

整个包 600 多行，import 列表只有：

```
argparse  array  dataclasses  json  math  os  random  re  sys  time  typing  wave
```

全部标准库。`dependencies = []`，pip 装完一个包都不多。

---

## 装

```bash
pip install soundtrack          # 常规做法
```

**不装也行**——把 `soundtrack/` 这个目录拖到任何有 Python 的地方，直接就能用：

```bash
python -m soundtrack list
```

---

## 三十秒上手

```bash
python -m soundtrack info  examples/ui-fx.json   # 看时间轴
python -m soundtrack check examples/ui-fx.json   # 只校验，不渲染（快）
python -m soundtrack render examples/ui-fx.json -o ui.wav
```

```python
import soundtrack as st

score = st.load("cues.json")
st.render(score, "out.wav")          # 写文件
buf   = st.render_samples(score)     # 拿到 array('d') 自己做处理
```

---

## cues.json 长什么样

```json
{
  "name": "menu-loop",
  "bpm": 84,
  "sample_rate": 22050,
  "duration": 16.0,
  "master": 0.8,
  "tracks": [
    {
      "id": "melody",
      "instrument": "pluck",
      "gain": 0.45,
      "loop": 8.0,
      "notes": [
        {"t": 0.0, "pitch": "C4", "dur": 0.4},
        {"beat": 2, "pitch": "A4", "beats": 1.4}
      ]
    },
    {
      "id": "drums",
      "instrument": "kick",
      "loop": 8.0,
      "notes": [{"t": 0.0, "dur": 0.1}, {"t": 2.0, "dur": 0.1}]
    }
  ]
}
```

顶层字段：

| 字段 | 默认 | 说明 |
|---|---|---|
| `name` | `untitled` | 只出现在输出里 |
| `bpm` | `120` | 影响 `beat`/`beats` 的换算 |
| `sample_rate` | `22050` | 8000 给音效、22050 给 BGM、44100 要音质时 |
| `duration` | 按最后一个音推算 | 给它是个下限，兜底用 |
| `master` | `0.9` | 归一化后的峰值，超过会压回 1.0 |
| `tracks` | 必填 | 至少一条 |

轨道字段：

| 字段 | 默认 | 说明 |
|---|---|---|
| `id` | 必填 | 唯一 |
| `instrument` | `pluck` | 见下面的乐器表 |
| `notes` | 必填 | 音符数组，可以为空 |
| `gain` | `1.0` | 轨音量，混音时压峰值用 |
| `loop` | 无 | **秒**。设了它，整轨音符会按这个周期反复铺，游戏 BGM 就靠这个 |

音符字段（英文 key 的别名都能认，`t`=`time`=`at`，`dur`=`length`，`beat`=`beat`…）：

| 字段 | 默认 | 说明 |
|---|---|---|
| `t` | 必填（或给 `beat`） | 起始秒 |
| `pitch` | 无 | `'A4'`、`'C#3'`、`'Eb5'`。鼓轨可以不给；`null` 表示休止 |
| `dur` | 必填（或给 `beats`） | 时长秒 |
| `gain` | `1.0` | 音在轨内的音量 |

两个省事写法：

- `{"beat": 2, "beats": 1}` —— 用拍号写，跟着 bpm 走
- `["-"]` —— 一个字符串代表休止一小节

---

## 乐器

```bash
$ python -m soundtrack list
可用乐器（12）:
  bass  bell  blip  clap  click  hat  kick  lead  organ  pad  pluck  snare
```

| 乐器 | 用在哪 | 手感 |
|---|---|---|
| `pad` | 氛围垫、章节转场 | 软起音、两个泛音，长尾 |
| `organ` | 教堂/复古电子 | 三个泛音，稳 |
| `pluck` | 旋律、琶音 | 拨弦，短促 |
| `bass` | 低音 | 方波 + 380Hz 低通 |
| `lead` | 主旋律 | 锯齿波 + 抖动（vibrato） |
| `blip` | 报错音、滑屏 | 极短，能连发 |
| `bell` | 奖励、解锁 | 四个泛音，衰减很慢 |
| `click` | UI 点击 | 干脆的方波 |
| `kick` / `snare` / `hat` / `clap` | 鼓组 | kick 是扫频正弦，snare 是噪声+音高，hat 是高通噪声 |

音色参数在 `soundtrack/synth.py` 的 `INSTRUMENTS` 表里改，一行一个乐器。

---

## 时间轴直接变配乐

如果你的渲染流程本来就在吐时间戳（章节标记、事件点），不用再手敲一遍音符：

```json
{
  "name": "render-timeline",
  "cues": [
    {"t": 0.00, "label": "chapter"},
    {"t": 2.60, "label": "tap"},
    {"t": 3.40, "label": "correct"},
    {"t": 5.20, "label": "swipe"},
    {"t": 6.00, "label": "section"},
    {"t": 11.40, "label": "success"}
  ]
}
```

```bash
python -m soundtrack adapt examples/timeline-cues.json -o timeline.wav
```

`label` 里的关键词自动选乐器：

| label 含 | 乐器 | 音高 |
|---|---|---|
| `error` `fail` `wrong` `deny` `invalid` | blip | A2 |
| `back` `cancel` `close` `dismiss` | blip | F3 |
| `success` `correct` `right` `pass` `coin` `reward` `unlock` | bell | E5 |
| `start` `go` `begin` `confirm` `ok` `done` | blip | C5 |
| `chapter` `section` `title` `scene` `ending` | pad | A3 |
| `tap` `click` `select` `choose` `press` | click | A5 |
| `swipe` `drag` `scroll` `move` | blip | D5 |
| `whoosh` `swoosh` `reveal` `zoom` `expand` | pad | C4 |
| 其它 | pluck | D4 |

按 instrument 自动分轨。纯字符串 cue（`["tap", "success"]`）一拍一个排开。

---

## 在 iPhone / iPad 上用

这是它被写成零依赖的主要原因。两条路，都不需要越狱、不需要编译器。

### a-Shell（App Store 免费，Terminus 出品）

自带 Python 和 pip：

```bash
pip install soundtrack
python -m soundtrack list
python -m soundtrack render ~/Documents/cues.json -o ~/Documents/out.wav
```

`~/Documents` 在"文件"App 里看得到，生成的 wav 点开就能播（iOS 原生支持）。

### Pythonista / 任意 iOS Python

把 `soundtrack/` 目录放进"文件"App，然后在脚本里指一下路径：

```python
import sys
sys.path.append("/var/mobile/Library/Mobile Documents/com.../soundtrack")
import soundtrack as st
st.render(st.load("cues.json"), "out.wav")
```

### 体积参考（16-bit 单声道）

| 采样率 | 1 分钟 | 适合 |
|---|---|---|
| 8000 Hz | ~0.96 MB | UI 音效、提示音 |
| 22050 Hz | ~2.6 MB | BGM、配乐（默认） |
| 44100 Hz | ~5.3 MB | 要音质 |

一首曲子就是几个 KB 的 JSON 加一个几百 KB 的 wav，能整个塞进 git。

---

## 场景

- **游戏 / App UI 音效包** —— 点击、报错、奖励、返回，一次性生成一整套，全是纯文本，改一个音名重渲
- **游戏菜单 BGM** —— `loop` 字段让 8 秒的素材无限循环，不存在"循环点没对齐"的问题
- **教学 / 科普影片配乐** —— 跟渲染时间轴对齐，章节和事件点自动有声音
- **视频流水线** —— 跟 [code-to-film](https://github.com/nss2018/code-to-film) 的渲染流程配合，渲完就是现成的时间轴，`adapt` 直接吃
- **独立开发者的占位音乐** —— 现在就能有声音，不用等买素材

---

## API

```python
import soundtrack as st

st.load("cues.json")            # 读文件 -> Score（校验过了）
st.render(score, "out.wav")     # 合成并写 wav
st.render_samples(score)        # -> array('d')，取值 -1..1
st.from_cues([{"t":0,"label":"tap"}])   # 时间轴 -> Score
st.instruments()                # ['bass','bell',...]
st.note_to_midi("A4")           # 69
st.midi_to_freq(69)             # 440.0

score.summary()                 # 纯文本摘要，CLI 的 info 用它
```

出错时 `ScoreError` 一定带位置，不会甩个裸 `KeyError` 给你：

```
error: tracks[0].notes[2]: 音名 'H4' 不对，应该是 'A4' 这种
```

---

## 限制（说在前面）

- **单声道**。没做声像，没做多轨立体声。
- **不是采样器**。加载不了音色文件，只有 8 个内置合成音色。想做真实乐器请用 FluidSynth / 采样库。
- **没有 FX 链**。只有一个固定一阶低通和 ADSR，没有混响、延迟、滤波扫描。pad 的尾巴是用 release 凑的。
- **长曲子会慢**。纯 Python 逐采样，22050Hz 大概 2–3 倍实时（16 秒的 BGM 实测 2.1 秒渲完）。5 分钟以上的曲子建议降采样率或者分段渲。
- **不做音频分析**。它是"输入 JSON 出 wav"，不是播放器也不是 DAW。

---

## 开发

```bash
make test     # 53 个单测，1 秒跑完
make gate     # 测试 + 三个示例必须真的能渲出来
make demo     # 渲染全部示例到 build/
```

测试只用 `unittest`，不依赖 pytest，所以 iOS 上也能跑。

## License

MIT
