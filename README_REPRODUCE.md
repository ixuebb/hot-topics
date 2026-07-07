# VMR Idea Graph Reproducible Package

打包日期：2026-07-04  
原始项目：Video Moment Retrieval / Temporal Grounding 自动化论文调研、图谱分析与 Idea 预测系统  

## 这个包里有什么

```text
vmr_idea_repro_20260704/
  source/
    automation_platform/        # D:\自动化论文平台 的源码与前端项目
    codex_skills/
      paper-writing/            # 本地自动化论文撰写 skill 和脚本
  data/
    download_paper/             # 已下载论文目录，含 PDF、摘要、引言、figure/table 抽取结果
    idea_graph/                 # 细粒度问题/方法/idea 图谱结果
  scripts/
    run_idea_dashboard.ps1      # 启动前端
    verify_package.ps1          # 检查关键文件是否齐全
  logs/
    copy_*.log                  # 本次打包复制日志
```

## 快速启动前端

在 PowerShell 中运行：

```powershell
powershell -ExecutionPolicy Bypass -File D:\syz_autopaper\all_projects\vmr_idea_repro_20260704\scripts\run_idea_dashboard.ps1
```

然后访问：

```text
http://127.0.0.1:8765/
```

如果 8765 已被占用，可以传入其他端口：

```powershell
powershell -ExecutionPolicy Bypass -File D:\syz_autopaper\all_projects\vmr_idea_repro_20260704\scripts\run_idea_dashboard.ps1 -Port 8877
```

## 关键数据文件

图谱结果位于：

```text
data\idea_graph\
```

最重要的文件：

- `idea_opportunities_finegrained.json`：60 个细粒度 idea 候选。
- `paper_micro_cards_index.json`：论文级问题、方法、证据链卡片。
- `micro_problem_clusters.json`：核心微问题聚类。
- `micro_method_clusters.json`：微方法聚类。
- `IDEA_REPORT_10_TOPICS.md`：10 个候选题目、摘要和引言报告。

论文库位于：

```text
data\download_paper\
```

每篇论文通常包含：

- PDF；
- abstract / introduction / full text；
- `figures/extracted_clean/` 中的完整 figure 裁剪；
- `tables/extracted_clean/` 和 `tables/crops_clean/` 中的表格 Markdown/CSV/crop；
- BibTeX 或元数据文件。

## 重新生成 Idea 图谱

如果需要从论文库重新生成细粒度 idea graph，使用包内 skill：

```powershell
python D:\syz_autopaper\all_projects\vmr_idea_repro_20260704\source\codex_skills\paper-writing\scripts\build_finegrained_idea_graph.py `
  --strict `
  --library-root "D:\syz_autopaper\all_projects\vmr_idea_repro_20260704\data\download_paper" `
  --out-dir "D:\syz_autopaper\all_projects\vmr_idea_repro_20260704\data\idea_graph_rebuilt"
```

如果脚本版本不接受 `--library-root`，请先查看：

```powershell
python D:\syz_autopaper\all_projects\vmr_idea_repro_20260704\source\codex_skills\paper-writing\scripts\build_finegrained_idea_graph.py --help
```

原始项目默认论文库路径是：

```text
D:\syz_autopaper\auto_idea\video moment retrieval\download_paper
```

## 校验包完整性

```powershell
powershell -ExecutionPolicy Bypass -File D:\syz_autopaper\all_projects\vmr_idea_repro_20260704\scripts\verify_package.ps1
```

校验会检查：

- 前端入口是否存在；
- idea graph 关键 JSON 是否存在；
- 论文库目录是否存在；
- paper-writing skill 是否存在；
- 文件数量和大致体积。

## 注意

1. 这个包包含本地论文 PDF 和抽取结果，适合离线复刻当前系统。
2. 前端是静态页面，不需要 npm install；直接用 Python `http.server` 即可。
3. 若要完整复跑文献下载，需要网络和外部数据源；本包主要保证当前已有论文库和图谱结果可复用。
4. 当前图谱中的 idea 是候选研究方向，不代表实验已经完成。
