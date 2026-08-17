# 参与贡献指南（Knowledge Research Agent）

感谢您的关注！本指南涵盖环境搭建、协作流程与代码风格约定。

## 环境搭建

1. 参照 [快速开始](README.zh-CN.md#-快速开始) 启动后端（Python 3.11 + conda）、前端（Node 18+）与 Qdrant。
2. 开发无需 API Key —— Key 留空时项目运行在 **Mock 模式**（见 `.env.example`）。
3. 仅当调试检索/排序链路时才需下载本地模型（约 4.4GB）：

```bash
cd apps/api
python scripts/download_models.py
```

## 分支与提交规范

- 从 `main` 拉出语义化分支：`feat/query-router`、`fix/pdf-parser`、`docs/readme`
- 提交信息沿用现有风格：`<type>: <描述>`，type 取值 `feat` / `fix` / `docs` / `refactor` / `eval` / `chore`
- 保持提交聚焦 —— 每次提交只包含一个逻辑变更

## 测试

### CI 检查（push/PR 自动运行）

| 范围 | 命令 | 目录 |
|---|---|---|
| 后端语法+导入 | `python -m compileall -q app` | `apps/api` |
| 前端 lint | `npm run lint` | `apps/web` |
| 前端类型检查+构建 | `npm run build` | `apps/web` |

### 本地手动冒烟测试（需模型/服务）

```bash
cd apps/api
python scripts/smoke_test.py           # 全链路冒烟
python scripts/router_test.py          # 查询路由
python scripts/kb_rag_test.py          # 知识库 RAG
python scripts/multi_source_test.py    # 多源检索
```

### 评估

```bash
cd apps/api
python eval/scripts/eval_dataset_gen.py 40
python eval/scripts/eval_run.py --gen 10 --save-baseline
```

## 代码风格

- **后端**：沿用现有模块划分（`agents` / `rag` / `llm` / `services` / `api` / `models`）；配置项写入 `.env.example`；代码中不得出现密钥
- **前端**：组件放入 `src/components/<分组>/`，共享状态放入 `src/features/`；提交前先跑 `npm run lint`
- 图编排逻辑集中在 `app/agents/` —— 新增检索步骤时须同步更新评估体系

## 提交 Pull Request

1. 推送前在本地跑完上述 CI 检查
2. 按 [PR 模板](.github/PULL_REQUEST_TEMPLATE.md) 填写
3. 行为变更时同步更新文档（README / docs/）

## License

参与贡献即表示您同意将贡献内容以本项目 [MIT License](LICENSE) 授权。
