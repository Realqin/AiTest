import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  createTestCase,
  generateStandaloneCaseGenerator,
  getDictionaries,
  getStandaloneCaseGeneratorConfig,
} from "./api";

const TEXT = {
  smoke: "\u5192\u70df\u6d4b\u8bd5",
  functional: "\u529f\u80fd\u6d4b\u8bd5",
  boundary: "\u8fb9\u754c\u6d4b\u8bd5",
  exception: "\u5f02\u5e38\u6d4b\u8bd5",
  permission: "\u6743\u9650\u6d4b\u8bd5",
  security: "\u5b89\u5168\u6d4b\u8bd5",
  compatibility: "\u517c\u5bb9\u6027\u6d4b\u8bd5",
  p0: "\u9ad8\u7ea7",
  p1: "\u4e2d\u7ea7",
  p2: "\u4f4e\u7ea7",
  p3: "\u6700\u4f4e\u7ea7",
  kbReq: "\u9700\u6c42\u6587\u6863\u77e5\u8bc6\u5e93",
  kbHistory: "\u5386\u53f2\u7528\u4f8b\u77e5\u8bc6\u5e93",
  kbBug: "\u7f3a\u9677\u6848\u4f8b\u77e5\u8bc6\u5e93",
  kbApi: "\u63a5\u53e3\u6587\u6863\u77e5\u8bc6\u5e93",
  loadConfigError: "\u52a0\u8f7d\u751f\u6210\u914d\u7f6e\u5931\u8d25",
  noKnowledgeBase: "\u65e0",
  generatedMessage: "\u5df2\u751f\u6210\u6d4b\u8bd5\u7528\u4f8b\uff0c\u53ef\u7ee7\u7eed\u7f16\u8f91\u540e\u4fdd\u5b58\u3002",
  generateError: "\u751f\u6210\u7528\u4f8b\u5931\u8d25",
  noRowsError: "\u6682\u65e0\u53ef\u4fdd\u5b58\u7684\u7528\u4f8b",
  untitledCase: "\u672a\u547d\u540d\u7528\u4f8b",
  saveSuccessPrefix: "\u5df2\u4fdd\u5b58 ",
  saveSuccessSuffix: " \u6761\u7528\u4f8b",
  saveError: "\u4fdd\u5b58\u7528\u4f8b\u5931\u8d25",
  title: "\u751f\u6210\u7528\u4f8b",
  subtitle: "\u901a\u8fc7\u622a\u56fe\u3001\u8bf4\u660e\u6587\u5b57\u548c\u6d4b\u8bd5\u7c7b\u578b\uff0c\u76f4\u63a5\u751f\u6210\u72ec\u7acb\u6d4b\u8bd5\u7528\u4f8b\u3002",
  caseTypeLabel: "\u6d4b\u8bd5\u7c7b\u578b",
  knowledgeBaseLabel: "\u77e5\u8bc6\u5e93",
  kbHint: "\u652f\u6301\u591a\u9009\uff0c\u70b9\u51fb\u53f3\u4fa7 \u00d7 \u53ef\u5feb\u901f\u6e05\u7a7a",
  composerLabel: "\u622a\u56fe\u4e0e\u8865\u5145\u8bf4\u660e",
  screenshotHint: "\u652f\u6301\u76f4\u63a5\u7c98\u8d34\u56fe\u7247\uff0c\u6216\u70b9\u51fb + \u4e0a\u4f20\u622a\u56fe\u3002",
  screenshotSubHint: "\u9f20\u6807\u79fb\u5165\u7f29\u7565\u56fe\u53ef\u5220\u9664\uff0c\u751f\u6210\u65f6\u4f1a\u4e00\u8d77\u53d1\u7ed9\u6a21\u578b\u8bc6\u522b\u3002",
  imageTypeError: "\u4ec5\u652f\u6301\u4e0a\u4f20\u56fe\u7247\u6587\u4ef6",
  imageLimitError: "\u6700\u591a\u53ea\u80fd\u6dfb\u52a0 8 \u5f20\u622a\u56fe",
  promptLabel: "\u4eba\u5de5\u8865\u5145\u63d0\u793a\u8bcd",
  promptPlaceholder: "\u53d1\u9001\u622a\u56fe\u6216\u5728\u8fd9\u91cc\u8865\u5145\u9875\u9762\u573a\u666f\u3001\u4e1a\u52a1\u89c4\u5219\u3001\u64cd\u4f5c\u76ee\u6807\u3001\u98ce\u9669\u70b9\u7b49\u8bf4\u660e...",
  addCase: "\u65b0\u589e\u7528\u4f8b",
  generating: "\u751f\u6210\u4e2d...",
  regenerate: "\u751f\u6210/\u91cd\u65b0\u751f\u6210\u7528\u4f8b",
  saving: "\u4fdd\u5b58\u4e2d...",
  save: "\u4fdd\u5b58\u7528\u4f8b",
  serial: "\u5e8f\u53f7",
  testPoint: "\u6d4b\u8bd5\u70b9",
  caseTitle: "\u7528\u4f8b\u540d\u79f0",
  preconditions: "\u524d\u7f6e\u6761\u4ef6",
  steps: "\u6d4b\u8bd5\u6b65\u9aa4",
  expected: "\u9884\u671f\u7ed3\u679c",
  priority: "\u4f18\u5148\u7ea7",
  operations: "\u64cd\u4f5c",
  empty: "\u6682\u65e0\u7528\u4f8b\uff0c\u8bf7\u5148\u4e0a\u4f20\u622a\u56fe\u5e76\u70b9\u51fb\u201c\u751f\u6210/\u91cd\u65b0\u751f\u6210\u7528\u4f8b\u201d\uff0c\u6216\u624b\u52a8\u65b0\u589e\u3002",
  copy: "\u590d\u5236",
  delete: "\u5220\u9664",
  templateLabel: "\u9636\u6bb5\u7cfb\u7edf\u63d0\u793a\u8bcd",
  addImage: "+",
};

const DEFAULT_CASE_TYPE_OPTIONS = [
  { key: "smoke", value: TEXT.smoke },
  { key: "functional", value: TEXT.functional },
  { key: "boundary", value: TEXT.boundary },
  { key: "exception", value: TEXT.exception },
  { key: "permission", value: TEXT.permission },
  { key: "security", value: TEXT.security },
  { key: "compatibility", value: TEXT.compatibility },
];

const DEFAULT_PRIORITY_OPTIONS = [
  { key: "P0", value: TEXT.p0 },
  { key: "P1", value: TEXT.p1 },
  { key: "P2", value: TEXT.p2 },
  { key: "P3", value: TEXT.p3 },
];

const DEFAULT_KNOWLEDGE_BASES = [TEXT.kbReq, TEXT.kbHistory, TEXT.kbBug, TEXT.kbApi];
const MANUAL_CASE_REQUIREMENT_ID = "manual_case_root";
const MAX_IMAGES = 8;

function createEmptyCase(caseType = "") {
  return {
    test_point: "",
    title: "",
    preconditions: [],
    steps: [""],
    expected: [""],
    priority: "P2",
    case_type: caseType,
  };
}

function parseLines(value) {
  return String(value || "")
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function formatLines(value) {
  return Array.isArray(value) ? value.join("\n") : "";
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("read failed"));
    reader.readAsDataURL(file);
  });
}

export default function StandaloneCaseGeneratorPage({ onCasesChanged, onBack }) {
  const [caseTypeDicts, setCaseTypeDicts] = useState([]);
  const [templateName, setTemplateName] = useState("");
  const [templateContent, setTemplateContent] = useState("");
  const [prompt, setPrompt] = useState("");
  const [caseTypes, setCaseTypes] = useState([]);
  const [knowledgeBases, setKnowledgeBases] = useState([]);
  const [kbDropdownOpen, setKbDropdownOpen] = useState(false);
  const [imageItems, setImageItems] = useState([]);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const fileInputRef = useRef(null);

  const caseTypeOptions = useMemo(
    () => (caseTypeDicts.length ? caseTypeDicts : DEFAULT_CASE_TYPE_OPTIONS),
    [caseTypeDicts]
  );

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [dicts, config] = await Promise.all([
          getDictionaries("case_type"),
          getStandaloneCaseGeneratorConfig(),
        ]);
        if (cancelled) return;
        setCaseTypeDicts(Array.isArray(dicts) ? dicts : []);
        setTemplateName(config.template_name || "");
        setTemplateContent(config.template_content || "");
      } catch (err) {
        if (!cancelled) setError(err.message || TEXT.loadConfigError);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    async function handlePaste(event) {
      const items = Array.from(event.clipboardData?.items || []);
      const imageFiles = items
        .filter((item) => item.type.startsWith("image/"))
        .map((item) => item.getAsFile())
        .filter(Boolean);
      if (!imageFiles.length) return;
      event.preventDefault();
      await appendImages(imageFiles);
    }

    window.addEventListener("paste", handlePaste);
    return () => window.removeEventListener("paste", handlePaste);
  }, [imageItems.length]);

  const knowledgeBaseLabel = knowledgeBases.length ? knowledgeBases.join("\u3001") : TEXT.noKnowledgeBase;

  function toggleCaseType(key) {
    setCaseTypes((prev) =>
      prev.includes(key) ? prev.filter((item) => item !== key) : [...prev, key]
    );
  }

  function toggleKnowledgeBase(item) {
    setKnowledgeBases((prev) =>
      prev.includes(item) ? prev.filter((entry) => entry !== item) : [...prev, item]
    );
  }

  async function appendImages(files) {
    const validFiles = Array.from(files || []).filter((file) => file && String(file.type || "").startsWith("image/"));
    if (!validFiles.length) {
      setError(TEXT.imageTypeError);
      return;
    }
    if (imageItems.length + validFiles.length > MAX_IMAGES) {
      setError(TEXT.imageLimitError);
      return;
    }
    setError("");
    const nextItems = await Promise.all(
      validFiles.map(async (file, index) => ({
        id: `img-${Date.now()}-${index}-${Math.random().toString(16).slice(2, 8)}`,
        name: file.name || `image-${index + 1}.png`,
        dataUrl: await fileToDataUrl(file),
      }))
    );
    setImageItems((prev) => [...prev, ...nextItems]);
  }

  function removeImage(id) {
    setImageItems((prev) => prev.filter((item) => item.id !== id));
  }

  function addCase() {
    setRows((prev) => [...prev, createEmptyCase(caseTypes[0] || "functional")]);
  }

  function duplicateCase(index) {
    setRows((prev) => {
      const next = [...prev];
      const source = next[index];
      next.splice(index + 1, 0, {
        ...source,
        preconditions: [...(source.preconditions || [])],
        steps: [...(source.steps || [])],
        expected: [...(source.expected || [])],
      });
      return next;
    });
  }

  function deleteCase(index) {
    setRows((prev) => prev.filter((_, rowIndex) => rowIndex !== index));
  }

  function updateCase(index, patch) {
    setRows((prev) =>
      prev.map((item, rowIndex) => (rowIndex === index ? { ...item, ...patch } : item))
    );
  }

  async function generateCases() {
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const result = await generateStandaloneCaseGenerator({
        prompt,
        case_types: caseTypes,
        knowledge_bases: knowledgeBases,
        image_data_urls: imageItems.map((item) => item.dataUrl),
        use_knowledge_base: knowledgeBases.length > 0,
      });
      setRows(
        (result.generated_cases || []).map((item) => ({
          ...item,
          priority: item.priority || "P2",
          case_type: item.case_type || caseTypes[0] || "functional",
        }))
      );
      setTemplateName(result.template_name || "");
      setTemplateContent(result.template_content || "");
      setMessage(result.content || TEXT.generatedMessage);
    } catch (err) {
      setError(err.message || TEXT.generateError);
    } finally {
      setLoading(false);
    }
  }

  async function saveCases() {
    if (!rows.length) {
      setError(TEXT.noRowsError);
      return;
    }

    setSaving(true);
    setError("");
    setMessage("");
    try {
      for (const item of rows) {
        await createTestCase({
          requirement_id: MANUAL_CASE_REQUIREMENT_ID,
          module_id: "",
          title: item.title || TEXT.untitledCase,
          test_point: item.test_point || "",
          preconditions: item.preconditions || [],
          steps: item.steps || [],
          expected: item.expected || [],
          priority: item.priority || "P2",
          case_type: item.case_type || caseTypes[0] || "functional",
          stage: "",
          creator: "admin",
        });
      }
      setMessage(`${TEXT.saveSuccessPrefix}${rows.length}${TEXT.saveSuccessSuffix}`);
      if (onCasesChanged) onCasesChanged();
    } catch (err) {
      setError(err.message || TEXT.saveError);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="panel case-generator-page">
      <div className="case-stage-head standalone-generator-head">
        <div className="standalone-generator-head-left">
          <button type="button" className="back-link standalone-generator-back" onClick={onBack}>
            {"\u2190 \u8fd4\u56de"}
          </button>
          <div>
            <h3>{TEXT.title}</h3>
            <p>{TEXT.subtitle}</p>
          </div>
        </div>
      </div>

      {error && <div className="case-stage-lock-tip">{error}</div>}
      {message && <div className="policy-tip">{message}</div>}

      <div className="case-generation-panel">
        <div className="case-generation-controls">
          <div className="case-generation-row">
            <label className="case-stage-label required-inline">{TEXT.caseTypeLabel}</label>
            <div className="case-check-group">
              {caseTypeOptions.map((item) => (
                <label
                  key={item.key}
                  className={caseTypes.includes(item.key) ? "case-check-chip active" : "case-check-chip"}
                >
                  <input
                    type="checkbox"
                    checked={caseTypes.includes(item.key)}
                    onChange={() => toggleCaseType(item.key)}
                    disabled={loading || saving}
                  />
                  <span>{item.value}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="case-generation-row">
            <label className="case-stage-label">{TEXT.knowledgeBaseLabel}</label>
            <div className="case-kb-section">
              <div className="case-kb-dropdown">
                <button
                  type="button"
                  className={kbDropdownOpen ? "case-kb-dropdown-trigger active" : "case-kb-dropdown-trigger"}
                  onClick={() => setKbDropdownOpen((prev) => !prev)}
                  disabled={loading || saving}
                >
                  <span
                    className={knowledgeBases.length ? "case-kb-dropdown-value" : "case-kb-dropdown-value placeholder"}
                  >
                    {knowledgeBaseLabel}
                  </span>
                  <span className="case-kb-dropdown-tools">
                    {knowledgeBases.length > 0 && (
                      <span
                        className="case-kb-dropdown-clear"
                        onClick={(event) => {
                          event.stopPropagation();
                          setKnowledgeBases([]);
                        }}
                        role="button"
                        tabIndex={0}
                      >
                        {"\u00d7"}
                      </span>
                    )}
                    <span className="case-kb-dropdown-arrow">{kbDropdownOpen ? "\u25b2" : "\u25bc"}</span>
                  </span>
                </button>
                {kbDropdownOpen && (
                  <div className="case-kb-dropdown-menu">
                    <div className="case-kb-dropdown-hint">{TEXT.kbHint}</div>
                    {DEFAULT_KNOWLEDGE_BASES.map((item) => (
                      <label
                        key={item}
                        className={knowledgeBases.includes(item) ? "case-kb-option active" : "case-kb-option"}
                      >
                        <input
                          type="checkbox"
                          checked={knowledgeBases.includes(item)}
                          onChange={() => toggleKnowledgeBase(item)}
                          disabled={loading || saving}
                        />
                        <span>{item}</span>
                      </label>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="case-generation-row case-composer-row">
            <label className="case-stage-label">{TEXT.composerLabel}</label>
            <div className="case-composer-wrap">
              <div
                className={imageItems.length ? "case-composer has-images" : "case-composer"}
                onDragOver={(event) => event.preventDefault()}
                onDrop={async (event) => {
                  event.preventDefault();
                  await appendImages(event.dataTransfer?.files || []);
                }}
              >
                {imageItems.length > 0 && (
                  <div className="case-composer-images">
                    {imageItems.map((item) => (
                      <div key={item.id} className="case-image-card composer-card">
                        <img src={item.dataUrl} alt={item.name} />
                        <button
                          type="button"
                          className="case-image-remove"
                          onClick={() => removeImage(item.id)}
                          disabled={loading || saving}
                          aria-label={TEXT.delete}
                        >?</button>
                      </div>
                    ))}
                  </div>
                )}

                <textarea
                  className="case-composer-input"
                  value={prompt}
                  onChange={(event) => setPrompt(event.target.value)}
                  placeholder={TEXT.promptPlaceholder}
                  readOnly={loading || saving}
                />

                <div className="case-composer-footer">
                  <button
                    type="button"
                    className="case-image-add composer-add"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={loading || saving}
                    aria-label={TEXT.screenshotHint}
                  >
                    <span>{TEXT.addImage}</span>
                  </button>
                  <div className="case-composer-hint">{TEXT.screenshotHint}</div>
                  <button
                    type="button"
                    className="case-composer-send"
                    onClick={generateCases}
                    disabled={loading || saving}
                    aria-label={TEXT.regenerate}
                  >?</button>
                </div>

                <input
                  ref={fileInputRef}
                  className="hidden-input"
                  type="file"
                  accept="image/*"
                  multiple
                  onChange={async (event) => {
                    await appendImages(event.target.files || []);
                    event.target.value = "";
                  }}
                />
              </div>
              <div className="case-image-subtip">{TEXT.screenshotSubHint}</div>
            </div>
          </div>

          <div className="case-generation-actions">
            <button type="button" className="btn ghost" onClick={addCase} disabled={loading || saving}>
              {TEXT.addCase}
            </button>
            <button type="button" className="btn action" onClick={saveCases} disabled={loading || saving}>
              {saving ? TEXT.saving : TEXT.save}
            </button>
          </div>
        </div>

        <div className="case-list-shell">
          <div className="case-list-scroll">
            <table className="case-edit-table">
              <thead>
                <tr>
                  <th>{TEXT.serial}</th>
                  <th>{TEXT.testPoint}</th>
                  <th>{TEXT.caseTitle}</th>
                  <th>{TEXT.preconditions}</th>
                  <th>{TEXT.steps}</th>
                  <th>{TEXT.expected}</th>
                  <th>{TEXT.priority}</th>
                  <th>{TEXT.caseTypeLabel}</th>
                  <th>{TEXT.operations}</th>
                </tr>
              </thead>
              <tbody>
                {rows.length === 0 && (
                  <tr>
                    <td colSpan="9" className="empty">
                      {TEXT.empty}
                    </td>
                  </tr>
                )}
                {rows.map((item, index) => (
                  <tr key={`standalone-case-row-${index}`}>
                    <td>{index + 1}</td>
                    <td>
                      <textarea
                        className="case-cell-textarea compact"
                        value={item.test_point || ""}
                        onChange={(event) => updateCase(index, { test_point: event.target.value })}
                        readOnly={loading || saving}
                      />
                    </td>
                    <td>
                      <textarea
                        className="case-cell-textarea compact"
                        value={item.title || ""}
                        onChange={(event) => updateCase(index, { title: event.target.value })}
                        readOnly={loading || saving}
                      />
                    </td>
                    <td>
                      <textarea
                        className="case-cell-textarea"
                        value={formatLines(item.preconditions)}
                        onChange={(event) => updateCase(index, { preconditions: parseLines(event.target.value) })}
                        readOnly={loading || saving}
                      />
                    </td>
                    <td>
                      <textarea
                        className="case-cell-textarea"
                        value={formatLines(item.steps)}
                        onChange={(event) => updateCase(index, { steps: parseLines(event.target.value) })}
                        readOnly={loading || saving}
                      />
                    </td>
                    <td>
                      <textarea
                        className="case-cell-textarea"
                        value={formatLines(item.expected)}
                        onChange={(event) => updateCase(index, { expected: parseLines(event.target.value) })}
                        readOnly={loading || saving}
                      />
                    </td>
                    <td>
                      <select
                        value={item.priority || "P2"}
                        onChange={(event) => updateCase(index, { priority: event.target.value })}
                        disabled={loading || saving}
                      >
                        {DEFAULT_PRIORITY_OPTIONS.map((priority) => (
                          <option key={priority.key} value={priority.key}>
                            {`${priority.key} - ${priority.value}`}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <select
                        value={item.case_type || "functional"}
                        onChange={(event) => updateCase(index, { case_type: event.target.value })}
                        disabled={loading || saving}
                      >
                        {Array.from(
                          new Set([
                            ...(caseTypes.length ? caseTypes : caseTypeOptions.map((type) => type.key)),
                            item.case_type || "functional",
                          ].filter(Boolean))
                        ).map((type) => {
                          const matched = caseTypeOptions.find((entry) => entry.key === type);
                          return (
                            <option key={type} value={type}>
                              {matched?.value || type}
                            </option>
                          );
                        })}
                      </select>
                    </td>
                    <td>
                      <div className="case-row-actions">
                        <button type="button" className="link" onClick={() => duplicateCase(index)} disabled={loading || saving}>
                          {TEXT.copy}
                        </button>
                        <button type="button" className="link link-danger" onClick={() => deleteCase(index)} disabled={loading || saving}>
                          {TEXT.delete}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <label className="case-stage-label">
          {`${TEXT.templateLabel}${templateName ? `\uff08${templateName}\uff09` : ""}`}
        </label>
        <textarea className="case-stage-template" value={templateContent} readOnly />
      </div>
    </section>
  );
}

