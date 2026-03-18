import React, { useEffect, useMemo, useState } from "react";
import {
  createPromptTemplate,
  deletePromptTemplate,
  getPromptTemplates,
  togglePromptTemplate,
  updatePromptTemplate,
} from "./api";

const PROMPT_TYPES = ["通用对话", "需求评审", "测试用例", "缺陷分析"];

const EMPTY_FORM = {
  prompt_type: PROMPT_TYPES[0],
  name: "",
  description: "",
  content: "",
};

function shortenText(value, limit = 34) {
  if (!value) return "-";
  return value.length > limit ? `${value.slice(0, limit)}...` : value;
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

  function openCreate() {
    setEditingItem(null);
    setForm(EMPTY_FORM);
    setShowModal(true);
  }

  function openEdit(item) {
    setEditingItem(item);
    setForm({
      prompt_type: item.prompt_type,
      name: item.name,
      description: item.description || "",
      content: item.content,
    });
    setShowModal(true);
  }

  async function submitForm() {
    try {
      setError("");
      if (editingItem) {
        await updatePromptTemplate(editingItem.id, form);
      } else {
        await createPromptTemplate(form);
      }
      setShowModal(false);
      setEditingItem(null);
      setForm(EMPTY_FORM);
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
        <h2>{"提示词管理"}</h2>
        <button className="btn action" onClick={openCreate}>{"+ 新增"}</button>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <section className="panel table-wrap">
        <table className="data-table admin-table">
          <thead>
            <tr>
              <th>序号</th>
              <th>{"类型"}</th>
              <th>{"提示词名称"}</th>
              <th>{"提示词内容"}</th>
              <th>{"备注"}</th>
              <th>{"状态"}</th>
              <th>{"操作"}</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && (
              <tr>
                <td colSpan="7" className="empty">{"暂无提示词数据"}</td>
              </tr>
            )}
            {items.map((item, index) => (
              <tr key={item.id}>
                <td>{index + 1}</td>
                <td>{item.prompt_type}</td>
                <td>{item.name}</td>
                <td title={item.content}><span className="table-cell-truncate">{shortenText(item.content, 34)}</span></td>
                <td>{item.remark || "未设置"}</td>
                <td>
                  <button
                    type="button"
                    className={item.enabled ? "admin-switch active" : "admin-switch"}
                    onClick={() => handleToggle(item)}
                  >
                    <span className="admin-switch-text">{item.enabled ? "已激活" : "未激活"}</span>
                  </button>
                </td>
                <td>
                  <button className="mini-btn" onClick={() => openEdit(item)}>{"编辑"}</button>
                  <button className="mini-btn danger" onClick={() => handleDelete(item)}>{"删除"}</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="pagination right">
          <div>{`共 ${items.length} 条`}</div>
          <div className="pagination-actions">
            <span>1</span>
            <span>{"10 条/页"}</span>
          </div>
        </div>
      </section>

      {showModal && (
        <div className="modal-mask">
          <div className="modal-card prompt-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{modalTitle}</h3>
              <button className="modal-close" onClick={() => setShowModal(false)}>x</button>
            </div>
            <div className="modal-body prompt-form-body">
              <label><span className="required">*</span>{"提示词类型"}</label>
              <select value={form.prompt_type} onChange={(e) => setForm((prev) => ({ ...prev, prompt_type: e.target.value }))}>
                {PROMPT_TYPES.map((item) => (
                  <option key={item} value={item}>{item}</option>
                ))}
              </select>

              <label><span className="required">*</span>{"提示词名称"}</label>
              <input value={form.name} onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))} />

              <label>{"描述"}</label>
              <input value={form.description} onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))} />

              <label><span className="required">*</span>{"提示词内容"}</label>
              <div className="prompt-editor-wrap">
                <textarea rows={12} value={form.content} onChange={(e) => setForm((prev) => ({ ...prev, content: e.target.value }))} />
                <div className="text-counter">{`${form.content.length}/10000`}</div>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn ghost" onClick={() => setShowModal(false)}>{"取消"}</button>
              <button className="btn action" onClick={submitForm} disabled={!form.name || !form.content}>{"保存"}</button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
