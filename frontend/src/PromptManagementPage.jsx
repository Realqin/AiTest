import React, { useEffect, useMemo, useState } from "react";
import {
  createPromptTemplate,
  deletePromptTemplate,
  getPromptTemplates,
  togglePromptTemplate,
  updatePromptTemplate,
} from "./api";

const PROMPT_TYPE_OPTIONS = ["通用对话", "需求评审", "测试用例", "缺陷分析"];

const PROMPT_NAME_OPTIONS = {
  "\u901a\u7528\u5bf9\u8bdd": ["\u9ed8\u8ba4\u6d4b\u8bd5\u52a9\u624b"],
  "\u9700\u6c42\u8bc4\u5ba1": ["\u53ef\u6d4b\u6027\u5206\u6790", "\u53ef\u884c\u6027\u5206\u6790", "\u903b\u8f91\u5206\u6790", "\u6e05\u6670\u5ea6\u5206\u6790"],
  "\u6d4b\u8bd5\u7528\u4f8b": ["\u6d4b\u8bd5\u7528\u4f8b-\u9700\u6c42\u62c6\u89e3", "\u6d4b\u8bd5\u7528\u4f8b-\u6d4b\u8bd5\u70b9\u68b3\u7406", "\u6d4b\u8bd5\u7528\u4f8b-\u751f\u6210\u7528\u4f8b"],
  "\u7f3a\u9677\u5206\u6790": ["\u7f3a\u9677\u5206\u6790-\u6839\u56e0\u5b9a\u4f4d", "\u7f3a\u9677\u5206\u6790-\u4fee\u590d\u5efa\u8bae"],
};

const RESPONSE_TYPE_PRESETS = [
  {
    value: "",
    label: "未指定",
    format: "",
  },
  {
    value: "markdown",
    label: "Markdown 正文",
    format: "使用 Markdown 正文输出，按标题和项目符号组织内容。",
  },
  {
    value: "markdown-table",
    label: "Markdown 表格",
    format: "使用 Markdown 表格输出，并补充必要说明。",
  },
  {
    value: "json-object",
    label: "JSON 对象",
    format: '{\n  "content": ""\n}',
  },
  {
    value: "json-array",
    label: "JSON 数组",
    format: '[\n  {\n    "name": "",\n    "value": ""\n  }\n]',
  },
  {
    value: "plain-text",
    label: "纯文本",
    format: "使用纯文本输出，不要使用 Markdown 标记。",
  },
];

const EMPTY_FORM = {
  prompt_type: PROMPT_TYPE_OPTIONS[0],
  name: PROMPT_NAME_OPTIONS[PROMPT_TYPE_OPTIONS[0]][0],
  description: "",
  base_content: "",
  response_type: "",
  response_format: "",
  enabled: true,
  is_default: false,
};

function shortenText(value, limit = 34) {
  if (!value) return "-";
  return value.length > limit ? `${value.slice(0, limit)}...` : value;
}

function getResponseTypeLabel(value) {
  return RESPONSE_TYPE_PRESETS.find((item) => item.value === value)?.label || value || "-";
}

function ensureOption(options, value) {
  if (!value) return options;
  return options.includes(value) ? options : [...options, value];
}

export default function PromptManagementPage() {
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);

  const modalTitle = useMemo(
    () => (editingItem ? "编辑提示词" : "新增提示词"),
    [editingItem],
  );

  const nameOptions = useMemo(
    () => ensureOption(PROMPT_NAME_OPTIONS[form.prompt_type] || [], form.name),
    [form.prompt_type, form.name],
  );

  async function loadItems() {
    try {
      setError("");
      const list = await getPromptTemplates();
      setItems(list || []);
    } catch (e) {
      setError(e.message || "加载提示词失败");
    }
  }

  useEffect(() => {
    loadItems();
  }, []);

  function closeModal() {
    setShowModal(false);
    setEditingItem(null);
    setForm(EMPTY_FORM);
  }

  function openCreate() {
    setEditingItem(null);
    setForm(EMPTY_FORM);
    setShowModal(true);
  }

  function openEdit(item) {
    const responseType = item.response_type || RESPONSE_TYPE_PRESETS[0].value;
    const presetFormat = RESPONSE_TYPE_PRESETS.find((option) => option.value === responseType)?.format || "";
    setEditingItem(item);
    setForm({
      prompt_type: item.prompt_type || PROMPT_TYPE_OPTIONS[0],
      name: item.name || "",
      description: item.description || "",
      base_content: item.base_content || item.content || "",
      response_type: responseType,
      response_format: item.response_format || presetFormat,
      enabled: Boolean(item.enabled),
      is_default: Boolean(item.is_default),
    });
    setShowModal(true);
  }

  function updateResponseType(nextType) {
    const preset = RESPONSE_TYPE_PRESETS.find((item) => item.value === nextType);
    setForm((prev) => ({
      ...prev,
      response_type: nextType,
      response_format: preset ? preset.format : prev.response_format,
    }));
  }

  function updatePromptType(nextType) {
    const defaultName = (PROMPT_NAME_OPTIONS[nextType] || [])[0] || "";
    setForm((prev) => ({
      ...prev,
      prompt_type: nextType,
      name: defaultName,
    }));
  }

  async function submitForm() {
    try {
      setError("");
      const payload = {
        prompt_type: form.prompt_type,
        name: form.name,
        description: form.description,
        base_content: form.base_content,
        response_type: form.response_type,
        response_format: form.response_format,
        remark: editingItem?.remark || "",
        enabled: form.enabled,
        is_default: form.is_default,
      };
      if (editingItem) {
        await updatePromptTemplate(editingItem.id, payload);
      } else {
        await createPromptTemplate(payload);
      }
      closeModal();
      await loadItems();
    } catch (e) {
      setError(e.message || "保存提示词失败");
    }
  }

  async function handleDelete(item) {
    try {
      setError("");
      await deletePromptTemplate(item.id);
      await loadItems();
    } catch (e) {
      setError(e.message || "删除提示词失败");
    }
  }

  async function handleToggle(item) {
    try {
      setError("");
      await togglePromptTemplate(item.id, !item.enabled);
      await loadItems();
    } catch (e) {
      setError(e.message || "切换提示词状态失败");
    }
  }

  return (
    <section className="admin-page">
      <div className="panel admin-page-header">
        <h2>提示词管理</h2>
        <button className="btn action" onClick={openCreate}>{"+ 新增"}</button>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <section className="panel table-wrap">
        <table className="data-table admin-table prompt-admin-table">
          <thead>
            <tr>
              <th>序号</th>
              <th>类型</th>
              <th>名称</th>
              <th>返回类型</th>
              <th>提示词内容</th>
              <th>返回格式</th>
              <th>描述</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && (
              <tr>
                <td colSpan="9" className="empty">暂无提示词数据</td>
              </tr>
            )}
            {items.map((item, index) => (
              <tr key={item.id}>
                <td>{index + 1}</td>
                <td>{item.prompt_type}</td>
                <td>{item.name}</td>
                <td>{getResponseTypeLabel(item.response_type)}</td>
                <td title={item.base_content || item.content}>
                  <span className="table-cell-truncate">{shortenText(item.base_content || item.content, 40)}</span>
                </td>
                <td title={item.response_format || ""}>
                  <span className="table-cell-truncate">{shortenText(item.response_format, 40)}</span>
                </td>
                <td>{item.description || "未设置"}</td>
                <td>
                  <button
                    type="button"
                    className={item.enabled ? "admin-switch active slim" : "admin-switch slim"}
                    onClick={() => handleToggle(item)}
                  >
                    <span className="admin-switch-text">{item.enabled ? "已启用" : "已停用"}</span>
                  </button>
                </td>
                <td>
                  <button className="mini-btn" onClick={() => openEdit(item)}>编辑</button>
                  <button className="mini-btn danger" onClick={() => handleDelete(item)}>删除</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {showModal && (
        <div className="modal-mask" onClick={closeModal}>
          <div className="modal-card prompt-modal prompt-config-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{modalTitle}</h3>
              <button className="modal-close" onClick={closeModal}>x</button>
            </div>
            <div className="modal-body prompt-form-body">
              <div className="prompt-inline-row">
                <label className="prompt-inline-label">
                  <span className="required">*</span>
                  <span>提示词类型</span>
                </label>
                <select value={form.prompt_type} onChange={(e) => updatePromptType(e.target.value)}>
                  {PROMPT_TYPE_OPTIONS.map((item) => (
                    <option key={item} value={item}>{item}</option>
                  ))}
                </select>
              </div>

              <div className="prompt-inline-row">
                <label className="prompt-inline-label">
                  <span className="required">*</span>
                  <span>提示词名称</span>
                </label>
                <select value={form.name} onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}>
                  {nameOptions.map((item) => (
                    <option key={item} value={item}>{item}</option>
                  ))}
                </select>
              </div>

              <label>描述</label>
              <input value={form.description} onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))} />

              <label><span className="required">*</span>提示词内容</label>
              <div className="prompt-editor-wrap">
                <textarea
                  rows={8}
                  value={form.base_content}
                  onChange={(e) => setForm((prev) => ({ ...prev, base_content: e.target.value }))}
                />
                <div className="text-counter">{`${form.base_content.length}/10000`}</div>
              </div>

              <div className="prompt-inline-row">
                <label className="prompt-inline-label">
                  <span>返回类型</span>
                </label>
                <select value={form.response_type} onChange={(e) => updateResponseType(e.target.value)}>
                  {RESPONSE_TYPE_PRESETS.map((item) => (
                    <option key={item.value} value={item.value}>{item.label}</option>
                  ))}
                </select>
              </div>

              <label>返回格式</label>
              <div className="prompt-editor-wrap">
                <textarea
                  rows={6}
                  value={form.response_format}
                  onChange={(e) => setForm((prev) => ({ ...prev, response_format: e.target.value }))}
                />
                <div className="text-counter">{`${form.response_format.length}/10000`}</div>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn ghost" onClick={closeModal}>取消</button>
              <button className="btn action" onClick={submitForm} disabled={!form.name || !form.base_content}>保存</button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
