# About AI Daily

软件测试与自动化执行流 GitHub 热点日报。每天从 GitHub 获取最近 24 小时和最近 7 天的热点项目，按 QA 自动化、E2E/API 测试、CI 执行流、代码质量等测试行业视角分类，生成 Markdown、HTML、SVG 海报和 JSON 归档。

## 当前能力

- GitHub Search API 采集测试/自动化/工程质量相关开源项目。
- 同时输出过去 24 小时热点和过去 7 天热点两个维度。
- 过滤商业营销、内容创作、非编程工程类项目。
- 输出 Markdown、HTML、SVG 海报和 JSON 归档。
- HTML 报告中的项目卡片可直接点击跳转 GitHub。
- CI 每天 UAE 时间上午 7 点自动执行，并自动生成 HTML 文件。

## 快速开始

```bash
cd /Users/qudong/Code/About_AI
python3 scripts/run_daily.py --config config/sources.example.json --hours 24
```

生成结果：

- `reports/YYYY-MM-DD.md`
- `reports/YYYY-MM-DD.html`
- `reports/YYYY-MM-DD-poster.svg`
- `data/items/YYYY-MM-DD.json`

## 可选环境变量

```bash
export GITHUB_TOKEN=ghp_xxx
```

本机配置默认使用 GitHub 账号 `DonnyQu7`。优先级：

1. `GITHUB_TOKEN`
2. `GH_TOKEN`
3. `gh auth token --hostname github.com --user DonnyQu7`

不配置 token 也能运行，但 GitHub 未认证请求的限额很低。当前本机 `git config --global user.name` 是 `DonnyQu7`，但如果 GitHub CLI 没有登录这个账号，需要先执行：

```bash
gh auth login -h github.com
```

## 定时运行

仓库内已经提供 GitHub Actions 配置：

- `.github/workflows/daily-report.yml`
- 默认每天 03:00 UTC 运行一次，等于 UAE 时间 07:00。
- 工作流会生成日报，并把 `reports/` 与 `data/items/` 强制提交回仓库。
- 每次运行会上传 artifact：`reports/YYYY-MM-DD.html`、`reports/YYYY-MM-DD-poster.svg` 和 `data/items/YYYY-MM-DD.json`。

## 本地验证

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

## 目录结构

```text
config/                 配置样例
docs/                   方案和设计文档
scripts/                命令行入口
src/about_ai_daily/     核心代码
tests/                  基础测试
reports/                Markdown / HTML / SVG 海报输出
data/items/             JSON 归档
```

## 下一步

- 增加 LLM 分类和摘要器。
- 增加 GitHub Star 增量跟踪。
- 增加推送渠道。
- 增加 Web Dashboard。
- 接入 X/Twitter 数据源。
