# Auto White Paper

GitHubリポジトリから学術論文を自動生成するCLIツール

## 概要

Auto White Paper (AWP) は、GitHubプロジェクトのURLを入力として、7章構成の学術論文を自動生成します。Claude APIを使用してコード解析と論文執筆を行います。

## 🚀 最短で論文を生成（コピペ用）

**前提**: `pip install auto-white-paper` でインストール済み、`ANTHROPIC_API_KEY` を環境変数に設定済み

```bash
# 学会論文（2-6ページ）を生成
mkdir my-paper && cd my-paper && \
awp init --github https://github.com/USER/REPO --language ja && \
sed -i '' 's/paper_type: conference/paper_type: conference/' awp.config.yaml && \
awp generate && awp export --format pdf
```

```bash
# ジャーナル論文（6-12ページ）を生成
mkdir my-paper && cd my-paper && \
awp init --github https://github.com/USER/REPO --language ja && \
sed -i '' 's/paper_type: conference/paper_type: journal/' awp.config.yaml && \
awp generate && awp export --format pdf
```

**最小限の手順**:
1. `mkdir my-paper && cd my-paper`
2. `echo "ANTHROPIC_API_KEY=sk-xxx" > .env`
3. `awp init --github https://github.com/USER/REPO`
4. `awp generate`

## 特徴

- **グローバルCLIツール**: 一度インストールすれば、どのディレクトリからでも使用可能
- **自動リポジトリ解析**: GitHubリポジトリをクローンし、コード構造・依存関係・アーキテクチャを分析
- **7章構成の論文生成**: Introduction から Conclusion まで、学術論文の標準構成に準拠
- **論文形式の選択**: Conference（2-6ページ）/ Journal（6-12ページ）
- **文献調査オプション**: 手動入力、Claude生成、またはGenspark API（利用可能な場合）
- **複数出力形式**: Markdown, LaTeX, PDF に対応
- **多言語対応**: 英語・日本語に対応

## 論文構成

| 章 | 内容 | 特記事項 |
|----|------|---------|
| 1 | Introduction | 文献調査、ストーリー構築 |
| 2 | Existing Methods | 数式表現、既存研究の整理 |
| 3 | Proposed Method | モデル提案、解析、開発フロー |
| 4 | Implementation | コード解析、図の自動生成 |
| 5 | Experiments | 条件設定、結果解析 |
| 6 | Discussion | 限界、実機検証の必要性 |
| 7 | Conclusion | まとめ |

## 論文形式

| 形式 | ページ数 | 用途 | 分量目安 |
|------|----------|------|---------|
| `conference` | 2-6ページ | 学会発表、国際会議 | 1,500-4,000語 |
| `journal` | 6-12ページ | ジャーナル投稿 | 4,000-8,000語 |

`awp.config.yaml` の `paper.paper_type` で設定:
```yaml
paper:
  paper_type: "conference"  # または "journal"
```

## インストール

### 前提条件

- Python 3.11以上
- LaTeX (PDF出力する場合)

### グローバルインストール

```bash
# pipでインストール
pip install auto-white-paper

# または、リポジトリからインストール
git clone https://github.com/yourusername/auto-white-paper.git
cd auto-white-paper
pip install .
```

### 開発モードでインストール

```bash
git clone https://github.com/yourusername/auto-white-paper.git
cd auto-white-paper
pip install -e ".[dev]"
```

## クイックスタート

### 1. 論文プロジェクトを初期化

```bash
# 論文を書くディレクトリを作成
mkdir my-research-paper
cd my-research-paper

# AWPプロジェクトを初期化
awp init --github https://github.com/user/repo --language ja
```

これにより以下のファイルが作成されます:
- `awp.config.yaml`: 設定ファイル
- `.env.example`: 環境変数テンプレート

### 2. APIキーを設定

```bash
cp .env.example .env
```

`.env` ファイルを編集:

```env
ANTHROPIC_API_KEY=your-anthropic-api-key-here
```

### 3. 論文を生成

```bash
# 全章を生成
awp generate

# 特定の章のみ生成
awp generate --chapters 1,2,3

# 生成前にリポジトリ情報を確認
awp analyze https://github.com/user/repo
```

### 4. 出力形式を選択

```bash
# PDF出力
awp export --format pdf

# LaTeX出力
awp export --format latex

# Markdown出力（デフォルト）
awp export --format markdown
```

## CLIコマンド

```bash
# プロジェクト初期化
awp init [PROJECT_NAME] --github <URL> --template <ieee|ieej|generic> --language <en|ja>

# リポジトリ解析（論文生成前の確認用）
awp analyze <GITHUB_URL>

# 論文生成
awp generate [--chapters <1,2,3...|all>] [--review] [--dry-run]

# 出力形式変換
awp export --format <pdf|latex|markdown> [--output <PATH>]

# 現在の状態を確認
awp status

# バージョン表示
awp version
```

## 設定ファイル

`awp.config.yaml` の構成:

```yaml
project:
  name: "My Research Paper"
  output_dir: "./output"

repository:
  url: "https://github.com/user/repo"
  branch: "main"

paper:
  template: "ieee"        # ieee, ieej, generic
  language: "ja"          # en, ja
  title: "論文タイトル"
  paper_type: "conference"  # conference (2-6 pages) or journal (6-12 pages)

llm:
  provider: "claude"
  model: "claude-sonnet-4-20250514"
  max_tokens: 4096
  temperature: 0.7
  literature_provider: "manual"  # genspark, manual, claude

output:
  formats: [markdown, latex, pdf]
```

## 文献調査プロバイダー

`llm.literature_provider` で文献調査の方法を選択できます:

### `manual` (推奨)

プロジェクトディレクトリ内の `.awp/literature/` フォルダにファイルを配置:

```
my-paper/
├── .awp/
│   └── literature/
│       ├── references.yaml
│       ├── findings.md
│       └── summary.txt
```

**references.yaml** の形式:
```yaml
- title: "Paper Title"
  authors: ["Author1", "Author2"]
  year: 2024
  venue: "Conference/Journal"
  doi: "10.1234/example"
```

**findings.md** の形式:
```markdown
- 関連研究の知見1
- 関連研究の知見2
```

### `claude`

Claude APIを使用して、リポジトリ情報から関連文献のレビューを生成します。

### `genspark`

Genspark APIが利用可能な場合、自動で文献検索を行います。

## プロジェクト構造

論文プロジェクトの構成:

```
my-paper/                    # 論文プロジェクトディレクトリ
├── awp.config.yaml         # 設定ファイル
├── .env                    # APIキー（gitignore推奨）
├── .awp/                   # AWP作業ディレクトリ
│   ├── repo/               # クローンしたリポジトリ
│   ├── cache/              # キャッシュ
│   └── literature/         # 手動文献情報
└── output/                 # 生成物
    ├── paper.md
    ├── paper.tex
    ├── paper.pdf
    └── figures/
```

## 出力例

生成される論文には以下が含まれます:

- **paper.md**: Markdown形式の論文
- **paper.tex**: LaTeX形式の論文
- **paper.pdf**: PDF形式の論文 (LaTeXコンパイル成功時)
- **figures/**: 自動生成された図 (アーキテクチャ図、フローチャートなど)

## Python API

直接Pythonから使用することもできます:

```python
import asyncio
from pathlib import Path
from awp.pipeline.orchestrator import PipelineOrchestrator, PipelineConfig
from awp.utils.config import get_settings

# 設定を読み込み
project_dir = Path("./my-paper")
settings = get_settings(project_dir)

# パイプライン設定
config = PipelineConfig(
    github_url="https://github.com/user/repo",
    output_dir=Path("./output"),
    language="ja",
    paper_title="My Research Paper",
)

# 論文生成
orchestrator = PipelineOrchestrator(config, settings, project_dir)
output_path = asyncio.run(orchestrator.run())
print(f"Paper generated: {output_path}")
```

## 開発

```bash
# 開発用依存関係をインストール
pip install -e ".[dev]"

# テスト実行
pytest

# リント
ruff check src/
black src/

# 型チェック
mypy src/
```

## 必要なAPIキー

| キー | 必須 | 説明 |
|------|------|------|
| ANTHROPIC_API_KEY | Yes | Claude API キー |
| GENSPARK_API_KEY | No | Genspark API キー (文献調査用) |
| GITHUB_TOKEN | No | プライベートリポジトリ用 |

## ライセンス

MIT License

## 貢献

Issue や Pull Request を歓迎します。
