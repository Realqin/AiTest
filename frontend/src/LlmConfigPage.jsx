import React, { useEffect, useMemo, useState } from "react";
import {
  createLlmConfig,
  deleteLlmConfig,
  fetchLlmModels,
  getLlmConfigs,
  testLlmConnection,
  toggleLlmConfig,
  updateLlmConfig,
} from "./api";

const EMPTY_FORM = {
  name: "",
  api_url: "",
  api_key: "",
  model_name: "",
  context_limit: 128000,
  vision_enabled: false,
  stream_enabled: true,
  enabled: false,
};

function formatTime(value) {
  return value ? value.replace("T", " ").slice(0, 19) : "-";
}

function shortenText(value, limit = 32) {
  if (!value) return "-";
  return value.length > limit ? `${value.slice(0, limit)}...` : value;
}

export default function LlmConfigPage() {
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [testing, setTesting] = useState(false);
  const [loadingModels, setLoadingModels] = useState(false);
  const [modelOptions, setModelOptions] = useState([]);
  const [testMessage, setTestMessage] = useState("");
  const [showApiKey, setShowApiKey] = useState(false);
  const [modelDropdownOpen, setModelDropdownOpen] = useState(false);

  const modalTitle = useMemo(
    () => (editingItem ? "编辑 LLM 配置" : "新增 LLM 配置"),
    [editingItem],
  );

  const filteredModelOptions = useMemo(() => {
    const keyword = form.model_name.trim().toLowerCase();
    return keyword
      ? modelOptions.filter((model) => model.toLowerCase().includes(keyword))
      : modelOptions;
  }, [form.model_name, modelOptions]);

  const canRefreshModels = Boolean(form.api_url && (editingItem || form.api_key));

  async function loadItems() {
    try {
      setError("");
      const list = await getLlmConfigs();
      setItems(list || []);
    } catch (e) {
      setError(e.message || "加载 LLM 配置失败");
    }
  }

  useEffect(() => {
    loadItems();
  }, []);

  useEffect(() => {
    if (!showModal || !editingItem?.id || !form.api_url) return;
    handleFetchModels();
  }, [showModal, editingItem?.id]);

  function openCreate() {
    setEditingItem(null);
    setForm(EMPTY_FORM);
    setShowApiKey(false);
    setModelOptions([]);
    setTestMessage("");
    setModelDropdownOpen(false);
    setShowModal(true);
  }

  function openEdit(item) {
    setEditingItem(item);
    setForm({
      name: item.name,
      api_url: item.api_url,
      api_key: "",
      model_name: item.model_name,
      context_limit: item.context_limit,
      vision_enabled: item.vision_enabled,
      stream_enabled: item.stream_enabled,
      enabled: item.enabled,
    });
    setShowApiKey(false);
    setModelOptions(item.model_name ? [item.model_name] : []);
    setTestMessage("");
    setModelDropdownOpen(false);
    setShowModal(true);
  }

  async function submitForm() {
    try {
      setError("");
      if (editingItem) {
        await updateLlmConfig(editingItem.id, form);
      } else {
        await createLlmConfig(form);
      }
      setShowModal(false);
      setEditingItem(null);
      setForm(EMPTY_FORM);
      setModelDropdownOpen(false);
      await loadItems();
    } catch (e) {
      setError(e.message || "保存 LLM 配置失败");
    }
  }

  async function handleDelete(item) {
    try {
      setError("");
      await deleteLlmConfig(item.id);
      await loadItems();
    } catch (e) {
      setError(e.message || "删除 LLM 配置失败");
    }
  }

  async function handleToggle(item) {
    try {
      setError("");
      await toggleLlmConfig(item.id, !item.enabled);
      await loadItems();
    } catch (e) {
      setError(e.message || "切换状态失败");
    }
  }

  async function handleFetchModels() {
    try {
      setLoadingModels(true);
      setTestMessage("");
      const result = await fetchLlmModels({
        api_url: form.api_url,
        api_key: form.api_key,
        config_id: editingItem?.id || null,
      });
      const nextOptions = result.items || [];
      setModelOptions(nextOptions);
      setModelDropdownOpen(true);
      setForm((prev) => ({
        ...prev,
        model_name: nextOptions.includes(prev.model_name) ? prev.model_name : (nextOptions[0] || ""),
      }));
      setTestMessage(`已拉取 ${nextOptions.length} 个模型`);
    } catch (e) {
      setTestMessage(e.message || "拉取模型列表失败");
    } finally {
      setLoadingModels(false);
    }
  }

  async function handleTestConnection() {
    try {
      setTesting(true);
      setTestMessage("");
      const result = await testLlmConnection({
        api_url: form.api_url,
        api_key: form.api_key,
        model_name: form.model_name,
        config_id: editingItem?.id || null,
      });
      setTestMessage(result.message || "测试连接成功");
    } catch (e) {
      setTestMessage(e.message || "测试连接失败");
    } finally {
      setTesting(false);
    }
  }

  return (
    <section className="admin-page">
      <div className="panel admin-page-header">
        <h2>{"LLM 配置管理"}</h2>
        <button className="btn action" onClick={openCreate}>{"+ 新增配置"}</button>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <section className="panel table-wrap">
        <table className="data-table admin-table">
          <thead>
            <tr>
              <th>序号</th>
              <th>{"配置名称"}</th>
              <th>{"模型名称"}</th>
              <th>API URL</th>
              <th>{"状态"}</th>
              <th>{"创建时间"}</th>
              <th>{"更新时间"}</th>
              <th>{"操作"}</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && (
              <tr>
                <td colSpan="8" className="empty">{"暂无 LLM 配置"}</td>
              </tr>
            )}
            {items.map((item, index) => (
              <tr key={item.id}>
                <td>{index + 1}</td>
                <td>{item.name}</td>
                <td>{item.model_name}</td>
                <td title={item.api_url}><span className="table-cell-truncate">{shortenText(item.api_url, 36)}</span></td>
                <td>
                  <button
                    type="button"
                    className={item.enabled ? "admin-switch status-switch active" : "admin-switch status-switch"}
                    onClick={() => handleToggle(item)}
                  >
                    <span className="admin-switch-text">{item.enabled ? "已激活" : "未激活"}</span>
                  </button>
                </td>
                <td>{formatTime(item.created_at)}</td>
                <td>{formatTime(item.updated_at)}</td>
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
          <div className="modal-card llm-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{modalTitle}</h3>
              <button className="modal-close" onClick={() => setShowModal(false)}>x</button>
            </div>
            <div className="modal-body llm-form-body">
              <label><span className="required">*</span>{"配置名称"}</label>
              <input value={form.name} onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))} />

              <div className="admin-form-grid two-columns">
                <div>
                  <label><span className="required">*</span>API URL</label>
                  <input value={form.api_url} onChange={(e) => setForm((prev) => ({ ...prev, api_url: e.target.value }))} />
                </div>
                <div>
                  <label>{editingItem ? "API Key" : "* API Key"}</label>
                  <div className="api-key-row">
                    <input
                      type={showApiKey ? "text" : "password"}
                      value={form.api_key}
                      placeholder={editingItem ? "留空不修改" : "请输入 API Key"}
                      onChange={(e) => setForm((prev) => ({ ...prev, api_key: e.target.value }))}
                    />
                    <button type="button" className="ghost-icon-btn" onClick={() => setShowApiKey((prev) => !prev)}>
                      {showApiKey ? "隐藏" : "显示"}
                    </button>
                  </div>
                </div>
              </div>

              <div className="admin-form-grid llm-model-row">
                <div className="admin-form-main-field">
                  <label><span className="required">*</span>{"模型名称"}</label>
                  <div className="model-select-row">
                    <div
                      className={modelDropdownOpen ? "model-combobox open" : "model-combobox"}
                      onBlur={() => window.setTimeout(() => setModelDropdownOpen(false), 120)}
                    >
                      <input
                        value={form.model_name}
                        placeholder={modelOptions.length > 0 ? "输入模型名称快速过滤" : "请先点击刷新获取模型"}
                        onFocus={() => setModelDropdownOpen(true)}
                        onChange={(e) => {
                          const value = e.target.value;
                          setForm((prev) => ({ ...prev, model_name: value }));
                          setModelDropdownOpen(true);
                        }}
                      />
                      {modelDropdownOpen && (
                        <div className="model-dropdown">
                          {filteredModelOptions.length > 0 ? (
                            filteredModelOptions.map((model) => (
                              <button
                                key={model}
                                type="button"
                                className={model === form.model_name ? "model-option active" : "model-option"}
                                onMouseDown={(e) => e.preventDefault()}
                                onClick={() => {
                                  setForm((prev) => ({ ...prev, model_name: model }));
                                  setModelDropdownOpen(false);
                                }}
                              >
                                {model}
                              </button>
                            ))
                          ) : (
                            <div className="model-option-empty">
                              {modelOptions.length > 0 ? "未找到匹配的模型" : "暂无模型，请先刷新列表"}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                    <button
                      type="button"
                      className="ghost-icon-btn refresh-btn"
                      onClick={handleFetchModels}
                      disabled={loadingModels || !canRefreshModels}
                      title="刷新模型列表"
                    >
                      {loadingModels ? "加载中..." : "刷新"}
                    </button>
                  </div>
                </div>
                <button type="button" className="btn ghost" onClick={handleTestConnection} disabled={testing}>
                  {testing ? "测试中..." : "测试连接"}
                </button>
              </div>

              {testMessage && <div className="form-help-text">{testMessage}</div>}

              <div className="admin-form-grid three-columns toggle-row-grid">
                <div>
                  <label>{"上下文限制"}</label>
                  <input
                    type="number"
                    value={form.context_limit}
                    onChange={(e) => setForm((prev) => ({ ...prev, context_limit: Number(e.target.value || 0) }))}
                  />
                </div>
                <div>
                  <label>{"多模态"}</label>
                  <button type="button" className={form.vision_enabled ? "admin-switch active slim form-switch" : "admin-switch slim form-switch"} onClick={() => setForm((prev) => ({ ...prev, vision_enabled: !prev.vision_enabled }))}>
                    <span className="admin-switch-text">Vision</span>
                  </button>
                </div>
                <div>
                  <label>{"流式输出"}</label>
                  <button type="button" className={form.stream_enabled ? "admin-switch active slim form-switch" : "admin-switch slim form-switch"} onClick={() => setForm((prev) => ({ ...prev, stream_enabled: !prev.stream_enabled }))}>
                    <span className="admin-switch-text">Stream</span>
                  </button>
                </div>
              </div>

            </div>
            <div className="modal-footer">
              <button className="btn ghost" onClick={() => setShowModal(false)}>{"取消"}</button>
              <button className="btn action" onClick={submitForm} disabled={!form.name || !form.api_url || !form.model_name || (!editingItem && !form.api_key)}>{"确定"}</button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
