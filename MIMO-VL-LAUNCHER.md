# Llama Monitor

当前版本默认使用 PyInstaller 目录版分发，以减小主 `exe` 文件体积。

## 正式输出

```text
dist\Llama Monitor\Llama Monitor.exe
```

请连同整个 `dist\Llama Monitor` 文件夹一起分发，不要只复制其中的 `exe`。

## 说明

- 主 `exe` 会比旧的单文件版本明显更小
- 运行依赖会放在同目录下的其他文件中
- 配置文件仍会写在 `exe` 所在目录，文件名为 `Llama Monitor-config.json`

## 构建

```powershell
python -m PyInstaller .\Mimo-VL-Launcher.spec
```
