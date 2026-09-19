# AgentCore ажиллагааны тайлан — Aether repo (2026-09-19)

## 1. Ажиллуулсан тохиргоо

| Зүйл | Утга |
|---|---|
| Командын оролт | `/agentcore .` |
| Framework | AgentCore (`~/.cline/skills/AgentCore`) — `OperationExecutor` contract |
| Adapter | `tools/agentcore_audit.py` → `WorkspaceEvidenceExecutor` (жинхэнэ командууд) |
| Task id | `aether_audit_final` |
| Горим | FULL (эцсийн), AUTO (хөгжүүлэлтийн үед) |
| Budget | 5.00 USD — зөвхөн **тооцоо**, жинхэнэ төлбөр биш |
| Үр дүн | **COMPLETED** — 5/5 unit, алдаагүй, 5 artifact |

**Зардлын үнэн зөв байдал:** нэг ч provider/LLM дуудагдаагүй; бүх ажил
детерминистик локал команд байсан тул `cost_source = "estimate"`
(5 × $0.01 = $0.05). Энэ нь **provider-аар баталгаажсан төлбөр БИШ**.

## 2. Бодит гүйцэтгэсэн ажил (P0–P4, бүгд COMPLETED)

| Unit | Төрөл | Хийсэн жинхэнэ үйлдэл |
|---|---|---|
| `unit_inspect` | parse | `RepositoryProcessor.inspect` + `fingerprint_repository` — 402 файл, SHA-256 `57d3…ff`, manifests, entry point, test dir |
| `unit_implementation` | code | `git status --porcelain`, `git diff --stat`, `git log -5` — ажлын модны бодит төлөв |
| `unit_validation` | test | `pytest`, `compileall`, `node --check` ×3 — бодит exit codes |
| `unit_polish` | polish | `git ls-files` hygiene, JSON валид байдал, `check_cog_coverage.py` |
| `unit_output` | output | Дээрх бүх бодит үр дүнгээс нэгтгэсэн тайлан (таамаг биш) |

### Validation-ийн бодит үр дүн (exit codes)

```
pytest tests -q                          exit=0   123 passed in 35.56s
compileall src backend tools tests main  exit=0   (алдаагүй)
node --check website/js/app.js           exit=0
node --check website/js/commands.js      exit=0
node --check website/js/config.js        exit=0
check_cog_coverage.py                    exit=0   36/36 cog, missing=[]
```

Structure audit: tracked файл 99, tracked junk **0**, хүчингүй JSON **0**,
`README.md` бүтцийн хэсэгтэй = True.

**Artifact-ууд (жинхэнэ файлууд):**

- `.agentcore/tasks/aether_audit_final/artifacts/result_unit_inspect.txt`
- `.agentcore/tasks/aether_audit_final/artifacts/output_unit_implementation.py`
- `.agentcore/tasks/aether_audit_final/artifacts/result_unit_validation.txt`
- `.agentcore/tasks/aether_audit_final/artifacts/result_unit_polish.txt`
- `.agentcore/tasks/aether_audit_final/artifacts/result_unit_output.txt`
- Тайлан: `.agentcore/outputs/aether_audit_final_report.md`
- Checkpoint: `.agentcore/checkpoints/aether_audit_final_manifest.json`

## 3. Resume (үргэлжлүүлэх) — 3 туршилтын бодит үр дүн

| Нөхцөл | `usage_history` | attempts | Үр дүн |
|---|---|---|---|
| Repo өөрчлөгдөөгүй (цэвэр resume) | **5** — дахин ажил хийгээгүй | 1 | COMPLETED — зөв, нэмэлт charge байхгүй |
| Repo өөрчлөгдсөн (1 файл) | **10** — 5 unit бүгд дахин | 2 | COMPLETED, гэхдээ ажил + төсөв давтагдсан |
| Repo өөрчлөгдсөн + тасарсан attempt | 7 | 2 | **FAILED**, `completed_work = []` → өөрөө сэргэхгүй |

## 4. Илэрсэн 5 сул тал (AgentCore framework, кодын түвшинд)

1. **Invalidation нь `attempt_count`-ыг reset хийдэггүй.** `_invalidate_changed_sources()`
   (`src/core/engine.py`) статусыг `completed → pending` болгодог ч
   `metadata.attempt_count`-ыг үлдээдэг. Иймд cumulative attempt нь
   `max_attempts = 2`-т хүрсэн unit-ыг scheduler дахин санал болгож, даалгавар
   шууд `FAILED / EXECUTION_ERROR` болно — дахин эхлүүлэх боломжгүй.
   *Баримт:* `errors: ['Unit unit_inspect exceeded max attempts (2)']`,
   `completed_work: []`, `completed_units: 0`.
2. **Fingerprint-ийн granularity хэт бүдүүн.** Repo нэг л "source" тул бүх unit
   бүтэн-repo SHA-256-ыг `source_refs`-д авдаг → нэг ч холбоогүй файл
   өөрчлөгдөхөд **бүх** ажил хүчингүй болж, дахин ажиллана
   ("granular invalidation" амлалт repository оролтод биелэхгүй).
   *Нэмэлт:* `RepositoryProcessor.IGNORED_DIRS`-д `logs/` байхгүй тул
   лог хавтсанд үүссэн `.txt` файл ч fingerprint-ыг өөрчилдөг.
3. **`manifest.validation` хэзээ ч бичигддэггүй.** Validation unit амжилттай
   ажилласан ч тайланд `_Validation not run or not applicable._` гарна —
   бодит exit codes зөвхөн artifact дотор байна.
4. **Тайлангийн буруу хэсэг.** `OutputManager.generate_report` нь
   `manifest.status != "completed"` (жижиг үсэг) харьцуулдаг ч engine
   `"COMPLETED"` (том) тавьдаг тул COMPLETED даалгаварт ч
   "Resume Information / Next pending unit: unit_output" хэвлэгддэг.
5. **Artifact-ийн нэршил.** `unit.type == "code"` бол текст хэлбэрийн evidence
   ч `output_unit_implementation.py` гэж `.py` өргөтгөлтэй хадгалагдана.

**Зэрэгцээ ажиллагааны эрсдэл (ажигласан):** нэг task id дээр хоёр процесс
зэрэг ажиллахад checkpoint interleave болж `FAILED` + `completed_work` устсан
(10 charge үлдсэн). Нэг task = нэг процесс байх ёстой.

## 5. Энэ ажиллагаанд хийсэн засвар (миний runner)

`tools/agentcore_audit.py`:

- **Lock файл** (`--force` override) — нэг checkpoint-д нэг бичигч.
- **Stale lock илрүүлэлт** — эзний PID амьд эсэхийг шалгаж (psutil → ctypes
  fallback) хуучирсан lock-ыг автоматаар устгана.
- **`--resume` үед lock буруу нэрлэгддэг байсан алдаа** — `aether_audit_<fp>`
  нэрээр хамгаалж, resume хийж буй checkpoint-ыг хамгаалахгүй байв → одоо
  `task_id = args.resume or args.task_id or <fingerprint>`.
- **`--reset`** — §4.1-ийн сэргэхгүй төлвөөс гарах зам: checkpoint + artifact
  устгаж цэвэр эхлүүлнэ.

## 6. Ажиллуулах заавар

```bash
# Шинэ audit
python tools/agentcore_audit.py . --task-id aether_audit_final --mode FULL --budget 5

# Үргэлжлүүлэх (repo өөрчлөгдөөгүй бол ажил давтахгүй)
python tools/agentcore_audit.py . --resume aether_audit_final

# FAILED/гэмтсэн төлвөөс сэргэх
python tools/agentcore_audit.py . --task-id aether_audit_final --reset --mode FULL
```

AgentCore өөр замд байвал `AGENTCORE_HOME` env-ээр заана.

## 7. Баталгаажаагүй / хязгаарлалт

- AgentCore-ийн provider adapter (`ProductionProviderExecutor`) дуудагдаагүй —
  жинхэнэ LLM ажиллагаа, жинхэнэ token/зардлын бүртгэл **шалгагдаагүй**.
- DOCX/XLSX/PPTX, image/video/audio дэмжлэг framework-д байхгүй (README-д
  тэмдэглэсэн); энэ audit-д хэрэглэгдээгүй.
- **CREDIT_SAFE** горим бодитоор туршигдаагүй (AUTO, FULL ажилласан).
- `.agentcore/` нь `.gitignore`-д нэмэгдсэн — commit хийгдэхгүй.