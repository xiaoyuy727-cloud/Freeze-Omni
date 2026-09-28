威慑# 发言时机调参(热加载,不用重启)

改 `./tuning.json` 里的数字,**约 2 秒后自动生效**,当前这段对话不用中断、不用重启服务。
每次数值变化会在服务端日志打印一行 `[tuning] reloaded: ... (was: ...)` 确认已生效。

```json
{
  "state_th1": 0.5,
  "state_th2": 0.5,
  "vad_threshold": 0.8,
  "vad_min_silence_ms": 2000,
  "vad_speech_pad_ms": 30
}
```

## 每个数字管什么

| 键 | 原值 | 原值所在代码 | 作用 | 调低 | 调高 |
|---|---|---|---|---|---|
| `state_th1` | 0.5 | `models/audioLLM.py` | 模型判"该我说话了"的门槛 | **爱抢话**,你还没说完它就接 | 更少开口,反应更迟,极端时不回应 |
| `state_th2` | 0.5 | `models/audioLLM.py` | 模型判"这轮结束/不值得回答"的门槛(优先级高于 th1) | 更容易把话头还给你、不回答 | 更容易硬答,哪怕你只是"嗯"了一声 |
| `vad_threshold` | 0.8 | `web/vad.py` | 多小的声音算"你在说话" | 更灵敏,小声也能触发,**但键盘声/噪声也可能被当人声** | 更迟钝,轻声/远讲可能完全没反应 |
| `vad_min_silence_ms` | 2000 | `web/vad.py` | 静音多久算这轮超时 | 更早放弃这一轮 | 更久才判超时 |
| `vad_speech_pad_ms` | 30 | `web/vad.py` | 语音前后补的静音边距 | 一般不用改 | 一般不用改 |

判定顺序(先 th2 后 th1):`state_2 > th2` → 结束这轮不回答;`state_1 > th1` → 开口回答;都没超过 → 继续听。

## 两个典型的"听感"配方

- **抢话版**(体验它插话的边界):`state_th1: 0.25`,`vad_threshold: 0.6`
- **迟钝版**(体验它等你彻底说完):`state_th1: 0.8`,`state_th2: 0.8`,`vad_threshold: 0.9`

同一句话在两组参数下各说一遍,对比最直观。

## 日志怎么看

服务端日志(带毫秒时间戳)里这几行,是判断"为什么它这样反应"的直接依据:

| 日志行 | 含义 |
|---|---|
| `State 1 prob: x, State 2 prob: y (th1=.., th2=..)` | 每 160ms 一次的判定原始概率 + 当前生效阈值 |
| `Vad start` | VAD 认为你开口了(前置门通过) |
| `Detect break` | 状态头判 `ss` → 它决定开口 |
| `Detect invalid break` | 状态头判 `el` → 它不打算回答这轮 |
| `Detect vad time out` | 你发声后 2 秒内没判出结果,这轮作废 |
| `Starting TTS` / `Codec Done` / `Send TTS data` | 语音合成与首包出音 |

归因方法:
- `State 1 prob` 提前越过 `th1` → **模型判断问题**(真·发言时机)
- 压根没有 `Vad start` → **VAD 漏检**(前置门没过,后面再准也没用)
- 两者都对但 `Detect break` 到出音隔很久 → **算力/排队延迟**,不是时机问题

## 回滚

本仓库改动集中在这几处,随时可还原:

```bash
git diff                 # 看全部改动
git checkout -- models/audioLLM.py web/vad.py web/resources/demo.html
rm -f tuning.py tuning.json TUNING.md bin/static/socket.io.min.js
```
