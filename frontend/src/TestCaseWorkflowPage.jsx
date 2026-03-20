import React, { useEffect, useMemo, useRef, useState } from "react";
import MindElixir from "mind-elixir";
import "mind-elixir/style.css";
import loadingGif from "./assets/loading.gif";
import {
  confirmTestCaseWorkflowStage,
  generateTestCaseWorkflowStage,
  getDictionaries,
  getTestCaseWorkflow,
  rollbackTestCaseWorkflowStage,
  updateTestCaseWorkflowDraft,
} from "./api";

const CASE_TYPE_DICT_OPTIONS = [
  { key: "smoke", value: "冒烟测试" },
  { key: "functional", value: "功能测试" },
  { key: "boundary", value: "边界测试" },
  { key: "exception", value: "异常测试" },
  { key: "permission", value: "权限测试" },
  { key: "security", value: "安全测试" },
  { key: "compatibility", value: "兼容性测试" },
];

const CASE_TYPE_LABEL_MAP = Object.fromEntries(CASE_TYPE_DICT_OPTIONS.map((item) => [item.key, item.value]));
const DEFAULT_PRIORITY_OPTIONS = [
  { key: "P0", value: "高级" },
  { key: "P1", value: "中级" },
  { key: "P2", value: "低级" },
  { key: "P3", value: "最低级" },
];

const DEFAULT_KNOWLEDGE_BASES = [
  "需求文档知识库",
  "历史用例知识库",
  "缺陷案例知识库",
  "接口文档知识库",
];

const PREVIEW_MINDMAP_THEME = {
  name: "AiTestPreview",
  type: "light",
  palette: ["#eb6a5b", "#f29d52", "#5fbf9f", "#5b9df2", "#8f6df2", "#46b7c9"],
  cssVar: {
    "--node-gap-x": "42px",
    "--node-gap-y": "16px",
    "--main-gap-x": "102px",
    "--main-gap-y": "46px",
    "--main-color": "#1f3452",
    "--main-bgcolor": "#fff4f1",
    "--main-bgcolor-transparent": "rgba(255,244,241,0.88)",
    "--color": "#32465f",
    "--bgcolor": "#f7fafc",
    "--selected": "#1677ff",
    "--accent-color": "#1677ff",
    "--root-color": "#132033",
    "--root-bgcolor": "#fffdf8",
    "--root-border-color": "#eb6a5b",
    "--root-radius": "20px",
    "--main-radius": "14px",
    "--topic-padding": "8px 14px",
    "--panel-color": "#31465f",
    "--panel-bgcolor": "#ffffff",
    "--panel-border-color": "#dbe5f0",
    "--map-padding": "44px",
  },
};

function getStageStatusLabel(stage) {
  if (stage.status === "confirmed") return "已确认";
  if (stage.status === "editing") return "进行中";
  return "未解锁";
}

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
  return (value || []).join("\n");
}

function mapCaseTypeOption(item) {
  return typeof item === "string" ? { key: item, value: CASE_TYPE_LABEL_MAP[item] || item } : item;
}

function normalizeDraftCase(caseItem) {
  return {
    ...caseItem,
    priority: caseItem?.priority || "",
    case_type: caseItem?.case_type || "",
  };
}

function normalizeDraftStage(stage) {
  return {
    content: stage.content || "",
    prompt: stage.prompt || "",
    generated_cases: (stage.generated_cases || []).map(normalizeDraftCase),
    case_types: stage.case_types || [],
    knowledge_bases: stage.knowledge_bases || [],
    use_knowledge_base: Boolean(stage.use_knowledge_base),
  };
}

function createMindNode(topic, direction) {
  return {
    id: `node-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    topic: topic || "未命名节点",
    expanded: true,
    direction,
    children: [],
  };
}

function collectRawMarkdownNodes(content) {
  const lines = String(content || "")
    .replace(/\r/g, "")
    .split("\n")
    .filter((line) => line.trim());

  return lines.map((rawLine) => {
    const line = rawLine.replace(/\t/g, "  ");
    const trimmed = line.trim();

    let rawLevel = 1;
    let topic = trimmed;
    let kind = "text";

    const headingMatch = trimmed.match(/^(#{1,6})\s+(.*)$/);
    const bulletMatch = line.match(/^(\s*)[-*+]\s+(.*)$/);
    const orderedMatch = line.match(/^(\s*)\d+\.\s+(.*)$/);

    if (headingMatch) {
      rawLevel = headingMatch[1].length;
      topic = headingMatch[2].trim();
      kind = "heading";
    } else if (bulletMatch) {
      rawLevel = Math.floor((bulletMatch[1] || "").length / 2) + 2;
      topic = bulletMatch[2].trim();
      kind = "bullet";
    } else if (orderedMatch) {
      rawLevel = Math.floor((orderedMatch[1] || "").length / 2) + 2;
      topic = orderedMatch[2].trim();
      kind = "ordered";
    } else {
      rawLevel = 2;
      topic = trimmed;
    }

    return { rawLevel, topic, kind };
  });
}

function parseMarkdownToMindData(content, title) {
  const nodes = collectRawMarkdownNodes(content);
  const root = {
    id: "root",
    topic: nodes.length ? "Mind Map" : (title || "Stage Analysis"),
    expanded: true,
    children: [],
  };
  const headingLevels = nodes.filter((item) => item.kind === "heading").map((item) => item.rawLevel);
  const headingBaseLevel = headingLevels.length ? Math.min(...headingLevels) : 1;
  const stack = [root];
  let currentHeadingLevel = 0;
  let topLevelCount = 0;

  nodes.forEach(({ rawLevel, topic, kind }) => {
    let level = 1;
    if (kind === "heading") {
      level = rawLevel - headingBaseLevel + 1;
      currentHeadingLevel = level;
    } else if (kind === "bullet" || kind === "ordered") {
      level = currentHeadingLevel > 0 ? currentHeadingLevel + Math.max(1, rawLevel - 1) : Math.max(1, rawLevel - 1);
    } else if (currentHeadingLevel > 0) {
      level = currentHeadingLevel + 1;
    }

    level = Math.max(1, Math.min(level, stack.length));
    while (stack.length > level) {
      stack.pop();
    }

    const parent = stack[stack.length - 1];
    const direction = level === 1
      ? (topLevelCount++ % 2 === 0 ? MindElixir.RIGHT : MindElixir.LEFT)
      : (parent.direction ?? MindElixir.RIGHT);
    const node = createMindNode(topic, direction);
    parent.children = parent.children || [];
    parent.children.push(node);
    stack[level] = node;
  });

  if (root.children?.length === 1) {
    const promotedRoot = {
      ...root.children[0],
      id: "root",
      direction: undefined,
    };
    (promotedRoot.children || []).forEach((child, index) => {
      child.direction = index % 2 === 0 ? MindElixir.RIGHT : MindElixir.LEFT;
    });
    return {
      nodeData: promotedRoot,
      direction: MindElixir.SIDE,
    };
  }

  return {
    nodeData: root,
    direction: MindElixir.SIDE,
  };
}

function serializeMindmapToMarkdown(mindData) {
  const root = mindData?.nodeData || mindData;
  const topNodes = root?.children || [];
  const lines = [];

  function walkBullet(node, depth) {
    const indent = "  ".repeat(depth);
    lines.push(`${indent}- ${String(node.topic || "").trim() || "未命名节点"}`);
    (node.children || []).forEach((child) => walkBullet(child, depth + 1));
  }

  topNodes.forEach((node, index) => {
    lines.push(`## ${String(node.topic || "").trim() || "未命名节点"}`);
    (node.children || []).forEach((child) => walkBullet(child, 0));
    if (index < topNodes.length - 1) lines.push("");
  });

  return lines.join("\n").trim();
}

function MindmapEditor({ title, content, editable, onChange }) {
  const containerRef = useRef(null);
  const instanceRef = useRef(null);
  const selectedNodeIdRef = useRef("");
  const lastContentRef = useRef(content || "");
  const onChangeRef = useRef(onChange);
  const [menuState, setMenuState] = useState({ visible: false, x: 0, y: 0 });
  const [selectedNodeId, setSelectedNodeId] = useState("");

  useEffect(() => {
    onChangeRef.current = onChange;
  }, [onChange]);

  function selectNodeElement(nodeEl) {
    const mind = instanceRef.current;
    if (!mind || !nodeEl) return;
    selectedNodeIdRef.current = nodeEl.nodeObj.id;
    setSelectedNodeId(nodeEl.nodeObj.id);
    mind.selectNode(nodeEl, true);
    syncSelectedHighlight(mind, nodeEl.nodeObj.id);
  }

  function syncSelectedHighlight(mind, nodeId) {
    const host = containerRef.current;
    if (!host) return;
    host.querySelectorAll("me-tpc.manual-selected").forEach((node) => node.classList.remove("manual-selected"));
    if (!nodeId) return;
    const nodeEl = mind.findEle(nodeId);
    nodeEl?.classList.add("manual-selected");
  }

  function syncMarkdown(mind) {
    const nextMarkdown = serializeMindmapToMarkdown(mind.getData());
    lastContentRef.current = nextMarkdown;
    onChangeRef.current(nextMarkdown);
  }

  useEffect(() => {
    if (!containerRef.current) return undefined;
    const mind = new MindElixir({
      el: containerRef.current,
      direction: MindElixir.SIDE,
      editable,
      contextMenu: false,
      toolBar: true,
      keypress: editable,
      mouseSelectionButton: 2,
      allowUndo: false,
      overflowHidden: true,
      handleWheel: false,
      scaleSensitivity: 0.08,
      scaleMax: 2.4,
      scaleMin: 0.35,
      alignment: "nodes",
      theme: PREVIEW_MINDMAP_THEME,
    });
    const initialContent = content || "";
    lastContentRef.current = initialContent;
    mind.init(parseMarkdownToMindData(initialContent, title));
    const mapContainer = containerRef.current.querySelector(".map-container");
    window.setTimeout(() => {
      mind.scaleFit();
      mind.toCenter();
      if (!editable) {
        const rect = mapContainer?.getBoundingClientRect?.() || containerRef.current.getBoundingClientRect();
        const targetScale = Math.min(1.12, Math.max(0.92, mind.scaleVal * 1.04));
        mind.scale(targetScale, {
          x: rect.left + rect.width / 2,
          y: rect.top + rect.height / 2,
        });
        mind.move(12, -16);
      }
    }, 0);
    instanceRef.current = mind;
    let dragging = false;
    let lastX = 0;
    let lastY = 0;
    const handleMouseDown = (event) => {
      if (editable) {
        const inputBox = containerRef.current?.querySelector?.("#input-box");
        if (inputBox && !event.target.closest?.("#input-box")) {
          inputBox.blur();
        }
      }
      if (event.button !== 0 || event.target.closest?.("me-tpc, me-epd")) return;
      dragging = true;
      lastX = event.clientX;
      lastY = event.clientY;
      mapContainer?.classList.add("is-dragging");
      event.preventDefault();
      setMenuState((prev) => ({ ...prev, visible: false }));
    };
    const handleClick = (event) => {
      if (!event.target.closest?.("me-tpc")) {
        setMenuState((prev) => ({ ...prev, visible: false }));
      }
      const nodeEl = event.target.closest?.("me-tpc");
      if (!nodeEl) return;
      selectNodeElement(nodeEl);
    };
    const handleDoubleClick = (event) => {
      if (!editable) return;
      const nodeEl = event.target.closest?.("me-tpc");
      if (!nodeEl) return;
      selectNodeElement(nodeEl);
      mind.beginEdit(nodeEl);
    };
    const handleContextMenu = (event) => {
      if (!editable) return;
      const nodeEl = event.target.closest?.("me-tpc");
      if (!nodeEl) return;
      event.preventDefault();
      const shellRect = containerRef.current?.getBoundingClientRect?.();
      selectNodeElement(nodeEl);
      setMenuState({
        visible: true,
        x: shellRect ? event.clientX - shellRect.left : event.clientX,
        y: shellRect ? event.clientY - shellRect.top : event.clientY,
      });
    };
    const handleMouseMove = (event) => {
      if (!dragging) return;
      const dx = event.clientX - lastX;
      const dy = event.clientY - lastY;
      lastX = event.clientX;
      lastY = event.clientY;
      mind.move(dx, dy);
    };
    const stopDragging = () => {
      dragging = false;
      mapContainer?.classList.remove("is-dragging");
    };
    const handleWheel = (event) => {
      event.preventDefault();
      const direction = event.deltaY < 0 ? 1 : -1;
      mind.scale(mind.scaleVal + direction * mind.scaleSensitivity, { x: event.clientX, y: event.clientY });
    };
    const handleOperation = (operation) => {
      if (!editable) return;
      if (["addChild", "removeNodes", "finishEdit", "moveNodeAfter", "moveNodeBefore", "moveNodeIn", "insertSibling"].includes(operation?.name)) {
        window.setTimeout(() => {
          const currentId = mind.currentNode?.nodeObj?.id || selectedNodeIdRef.current;
          if (currentId) {
            selectedNodeIdRef.current = currentId;
            setSelectedNodeId(currentId);
          }
          syncSelectedHighlight(mind, currentId);
          syncMarkdown(mind);
        }, 0);
      }
    };

    mapContainer?.addEventListener("mousedown", handleMouseDown);
    mapContainer?.addEventListener("click", handleClick);
    mapContainer?.addEventListener("dblclick", handleDoubleClick);
    mapContainer?.addEventListener("contextmenu", handleContextMenu);
    mapContainer?.addEventListener("wheel", handleWheel, { passive: false });
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", stopDragging);
    mapContainer?.addEventListener("mouseleave", stopDragging);
    mind.bus.addListener("operation", handleOperation);

    return () => {
      mapContainer?.removeEventListener("mousedown", handleMouseDown);
      mapContainer?.removeEventListener("click", handleClick);
      mapContainer?.removeEventListener("dblclick", handleDoubleClick);
      mapContainer?.removeEventListener("contextmenu", handleContextMenu);
      mapContainer?.removeEventListener("wheel", handleWheel);
      mapContainer?.removeEventListener("mouseleave", stopDragging);
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", stopDragging);
      mind.bus.removeListener("operation", handleOperation);
      instanceRef.current?.destroy();
      instanceRef.current = null;
    };
  }, [title, editable]);

  useEffect(() => {
    const mind = instanceRef.current;
    if (!mind) return;
    const nextContent = content || "";
    if (nextContent === lastContentRef.current) return;
    lastContentRef.current = nextContent;
    mind.refresh(parseMarkdownToMindData(nextContent, title));
    window.setTimeout(() => {
      const currentId = selectedNodeIdRef.current;
      if (currentId) {
        syncSelectedHighlight(mind, currentId);
        const selectedEl = mind.findEle(currentId);
        if (!selectedEl) {
          selectedNodeIdRef.current = "";
          setSelectedNodeId("");
        }
      }
    }, 0);
  }, [content, title]);

  return (
    <div className="mindmap-editor-shell">
      <div ref={containerRef} className="mind-elixir-host" />
      {editable && menuState.visible && (
        <div
          className="mindmap-context-menu"
          style={{ left: `${menuState.x}px`, top: `${menuState.y}px` }}
        >
          <button
            type="button"
            className="mindmap-context-menu-item"
            onClick={() => {
              const mind = instanceRef.current;
              const nodeEl = selectedNodeId ? mind?.findEle(selectedNodeId) : null;
              if (!mind || !nodeEl) return;
              selectNodeElement(nodeEl);
              mind.addChild(nodeEl);
              setMenuState((prev) => ({ ...prev, visible: false }));
            }}
            disabled={!selectedNodeId}
          >
            新增子节点
          </button>
          <button
            type="button"
            className="mindmap-context-menu-item danger"
            onClick={() => {
              const mind = instanceRef.current;
              const nodeEl = selectedNodeId ? mind?.findEle(selectedNodeId) : null;
              if (!mind || !nodeEl || !nodeEl.nodeObj?.parent) return;
              mind.selectNode(nodeEl, true);
              mind.removeNodes([nodeEl]);
              selectedNodeIdRef.current = "";
              setSelectedNodeId("");
              setMenuState((prev) => ({ ...prev, visible: false }));
            }}
            disabled={!selectedNodeId}
          >
            删除
          </button>
        </div>
      )}
    </div>
  );
}

function getInitialDrafts(stages = []) {
  return Object.fromEntries(stages.map((stage) => [stage.key, normalizeDraftStage(stage)]));
}

function getCaseTypeOptions(stage) {
  const options = stage?.case_type_options?.length ? stage.case_type_options : CASE_TYPE_DICT_OPTIONS;
  return options.map(mapCaseTypeOption);
}

function getPriorityOptions(stage, localOptions) {
  if (stage?.priority_options?.length) return stage.priority_options;
  return localOptions?.length ? localOptions : DEFAULT_PRIORITY_OPTIONS;
}

function getKnowledgeBaseOptions(stage) {
  return stage?.knowledge_base_options?.length ? stage.knowledge_base_options : DEFAULT_KNOWLEDGE_BASES;
}

function getRegenerateLabel(stage) {
  if (!stage) return "生成/重新生成";
  if (stage.key === "cases") return "生成/重新生成用例";
  return `生成/重新生成${stage.title || ""}`;
}

export default function TestCaseWorkflowPage({ requirementId, onBack, onCasesChanged }) {
  const [data, setData] = useState(null);
  const [drafts, setDrafts] = useState({});
  const [priorityOptions, setPriorityOptions] = useState([]);
  const [activeStageKey, setActiveStageKey] = useState("clarify");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState(null);
  const [kbDropdownOpen, setKbDropdownOpen] = useState(false);
  const [activeView, setActiveView] = useState("xmind");
  const [generatingStageKey, setGeneratingStageKey] = useState("");
  const noticeTimerRef = useRef(null);

  function showNotice(type, message) {
    setNotice({ type, message });
    window.clearTimeout(noticeTimerRef.current);
    noticeTimerRef.current = window.setTimeout(() => setNotice(null), 1000);
  }

  async function loadWorkflow() {
    setLoading(true);
    setError("");
    try {
      const next = await getTestCaseWorkflow(requirementId);
      setData(next);
      setDrafts(getInitialDrafts(next.workflow.stages));
      const activeStage =
        next.workflow.stages.find((item) => item.is_active)
        || next.workflow.stages[next.workflow.current_stage_index]
        || next.workflow.stages[0];
      setActiveStageKey((prev) => {
        const exists = next.workflow.stages.some((item) => item.key === prev && !item.is_locked);
        return exists ? prev : activeStage?.key || "clarify";
      });
    } catch (e) {
      setError(e.message || "加载测试用例流程失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadWorkflow();
  }, [requirementId]);

  useEffect(() => {
    getDictionaries("case_priority")
      .then((result) => setPriorityOptions(result.items || []))
      .catch(() => setPriorityOptions([]));
  }, []);

  useEffect(() => {
    setActiveView(activeStageKey === "cases" ? "text" : "xmind");
  }, [activeStageKey]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (!event.target.closest?.(".case-kb-dropdown")) {
        setKbDropdownOpen(false);
      }
    };
    window.addEventListener("mousedown", handleClickOutside);
    return () => {
      window.removeEventListener("mousedown", handleClickOutside);
      window.clearTimeout(noticeTimerRef.current);
    };
  }, []);

  const stages = data?.workflow?.stages || [];
  const activeStage = stages.find((item) => item.key === activeStageKey) || stages[0];
  const activeDraft = drafts[activeStage?.key] || normalizeDraftStage(activeStage || { key: "" });
  const canEdit = Boolean(activeStage && !activeStage.is_locked && activeStage.is_active);
  const caseTypeOptions = getCaseTypeOptions(activeStage);
  const casePriorityOptions = getPriorityOptions(activeStage, priorityOptions);
  const knowledgeBaseOptions = getKnowledgeBaseOptions(activeStage);
  const isGeneratingStage = Boolean(submitting && generatingStageKey === activeStage?.key);

  function patchDraft(stageKey, patch) {
    setDrafts((prev) => ({
      ...prev,
      [stageKey]: {
        ...(prev[stageKey] || normalizeDraftStage({ key: stageKey })),
        ...patch,
      },
    }));
  }

  function buildDraftPayload(stageKey, draft) {
    return {
      stage_key: stageKey,
      content: draft.content || "",
      prompt: draft.prompt || "",
      generated_cases: draft.generated_cases || [],
      case_types: draft.case_types || [],
      knowledge_bases: draft.knowledge_bases || [],
      use_knowledge_base: Boolean(draft.use_knowledge_base),
    };
  }

  async function submitAction(task) {
    setSubmitting(true);
    setError("");
    try {
      await task();
    } catch (e) {
      setError(e.message || "操作失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function saveDraft() {
    if (!activeStage) return;
    const payload = buildDraftPayload(activeStage.key, activeDraft);
    setSubmitting(true);
    setError("");
    try {
      const next = await updateTestCaseWorkflowDraft(requirementId, payload);
      setData(next);
      setDrafts(getInitialDrafts(next.workflow.stages));
      if (activeStage.key === "cases" && onCasesChanged) {
        onCasesChanged();
      }
      showNotice("success", "保存成功");
    } catch (e) {
      setError(e.message || "操作失败");
      showNotice("error", "保存失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function regenerateStage() {
    if (!activeStage) return;
    const payload = {
      stage_key: activeStage.key,
      prompt: activeDraft.prompt || "",
      case_types: activeDraft.case_types || [],
      knowledge_bases: activeDraft.knowledge_bases || [],
      use_knowledge_base: Boolean(activeDraft.use_knowledge_base),
    };
    setGeneratingStageKey(activeStage.key);
    if (activeStage.key === "cases") {
      setSubmitting(true);
      setError("");
      patchDraft(activeStage.key, {
        content: "",
        generated_cases: [],
      });
      try {
        const next = await generateTestCaseWorkflowStage(requirementId, payload);
        setData(next);
        setDrafts(getInitialDrafts(next.workflow.stages));
      } catch (e) {
        setError(e.message || "\u751f\u6210\u6d4b\u8bd5\u7528\u4f8b\u5931\u8d25");
      } finally {
        setGeneratingStageKey("");
        setSubmitting(false);
      }
      return;
    }
    try {
      await submitAction(async () => {
        const next = await generateTestCaseWorkflowStage(requirementId, payload);
        setData(next);
        setDrafts(getInitialDrafts(next.workflow.stages));
      });
    } finally {
      setGeneratingStageKey("");
    }
  }

  async function confirmStage() {
    if (!activeStage) return;
    await submitAction(async () => {
      const next = await confirmTestCaseWorkflowStage(
        requirementId,
        buildDraftPayload(activeStage.key, activeDraft),
      );
      setData(next);
      setDrafts(getInitialDrafts(next.workflow.stages));
      const nextActive =
        next.workflow.stages.find((item) => item.is_active)
        || next.workflow.stages.find((item) => item.key === activeStage.key)
        || next.workflow.stages[0];
      setActiveStageKey(nextActive?.key || activeStage.key);
      if (activeStage.key === "cases" && onCasesChanged) {
        onCasesChanged();
      }
    });
  }

  async function rollbackStage(stageKey) {
    await submitAction(async () => {
      const next = await rollbackTestCaseWorkflowStage(requirementId, { stage_key: stageKey });
      setData(next);
      setDrafts(getInitialDrafts(next.workflow.stages));
      setActiveStageKey(stageKey);
    });
  }

  function toggleCaseType(caseType) {
    const current = new Set(activeDraft.case_types || []);
    if (current.has(caseType)) {
      current.delete(caseType);
    } else {
      current.add(caseType);
    }
    patchDraft(activeStage.key, {
      case_types: Array.from(current),
    });
  }

  function toggleKnowledgeBase(name) {
    const current = new Set(activeDraft.knowledge_bases || []);
    if (current.has(name)) {
      current.delete(name);
    } else {
      current.add(name);
    }
    patchDraft(activeStage.key, {
      knowledge_bases: Array.from(current),
      use_knowledge_base: current.size > 0,
    });
  }

  function clearKnowledgeBases(event) {
    event.preventDefault();
    event.stopPropagation();
    patchDraft(activeStage.key, {
      knowledge_bases: [],
      use_knowledge_base: false,
    });
    setKbDropdownOpen(false);
  }

  function updateCase(index, patch) {
    const nextCases = (activeDraft.generated_cases || []).map((item, itemIndex) => (
      itemIndex === index ? { ...item, ...patch } : item
    ));
    patchDraft(activeStage.key, { generated_cases: nextCases });
  }

  function addCase() {
    patchDraft(activeStage.key, {
      generated_cases: [
        ...(activeDraft.generated_cases || []),
        createEmptyCase(activeDraft.case_types?.[0] || ""),
      ],
    });
  }

  function duplicateCase(index) {
    const target = activeDraft.generated_cases?.[index];
    if (!target) return;
    const next = [...(activeDraft.generated_cases || [])];
    next.splice(index + 1, 0, {
      ...target,
      title: target.title ? `${target.title}-副本` : "",
    });
    patchDraft(activeStage.key, { generated_cases: next });
  }

  function deleteCase(index) {
    patchDraft(activeStage.key, {
      generated_cases: (activeDraft.generated_cases || []).filter((_, itemIndex) => itemIndex !== index),
    });
  }

  const caseRows = useMemo(
    () => (activeDraft.generated_cases?.length ? activeDraft.generated_cases : []),
    [activeDraft.generated_cases],
  );
  const knowledgeBaseLabel = activeDraft.knowledge_bases?.length
    ? activeDraft.knowledge_bases.join("、")
    : "无";

  if (loading) {
    return <section className="panel placeholder"><p>正在加载测试用例生成流程...</p></section>;
  }

  if (!data) {
    return <section className="panel placeholder"><p>{error || "测试用例流程不存在"}</p></section>;
  }

  return (
    <section className="case-workflow-page">
      <div className="panel case-workflow-header">
        <div className="case-workflow-header-top">
          <button className="back-link" onClick={onBack}>{"← 返回需求列表"}</button>
          <div className="case-workflow-title-wrap">
            <h2>测试用例生成</h2>
            <p>{data.requirement.title}</p>
          </div>
          <div className="case-workflow-meta">
            <span className="tag info">{data.requirement.project || "未关联项目"}</span>
            <span className={data.workflow.completed ? "tag success" : "tag wait"}>
              {data.workflow.completed ? "流程已完成" : "流程进行中"}
            </span>
          </div>
        </div>

        <div className="case-stage-stepper">
          {stages.map((stage, index) => (
            <React.Fragment key={stage.key}>
              <button
                type="button"
                className={stage.key === activeStageKey ? `case-stage-node active ${stage.status}` : `case-stage-node ${stage.status}`}
                disabled={stage.is_locked}
                onClick={() => setActiveStageKey(stage.key)}
              >
                <span className="case-stage-icon">{stage.status === "confirmed" ? "✓" : index + 1}</span>
                <span className="case-stage-name">{stage.title}</span>
              </button>
              {index < stages.length - 1 && <div className="case-stage-line" />}
            </React.Fragment>
          ))}
        </div>
      </div>

      {notice && (
        <div className="floating-notice-wrap">
          <div className={notice.type === "success" ? "floating-notice success" : "floating-notice error"}>{notice.message}</div>
        </div>
      )}
      {error && <div className="error-banner">{error}</div>}

      <div className="case-workflow-layout">
        <div className={isGeneratingStage ? "panel case-workflow-main is-busy" : "panel case-workflow-main"}>
          {isGeneratingStage && (
            <div className="case-workflow-loading-mask">
              <img src={loadingGif} alt="\u751f\u6210\u4e2d" className="case-workflow-loading-image" />
            </div>
          )}
          {activeStage && (
            <>
              <div className="case-stage-head">
                <div>
                  <h3>{`第 ${stages.findIndex((item) => item.key === activeStage.key) + 1} 阶段：${activeStage.title}`}</h3>
                  <p>{activeStage.subtitle}</p>
                </div>
                <div className="case-stage-actions-top">
                  <span className={activeStage.status === "confirmed" ? "tag success" : activeStage.status === "editing" ? "tag info" : "tag wait"}>
                    {getStageStatusLabel(activeStage)}
                  </span>
                  {!activeStage.is_active && !activeStage.is_locked && (
                    <button type="button" className="btn ghost" onClick={() => rollbackStage(activeStage.key)} disabled={submitting}>
                      回退到当前阶段
                    </button>
                  )}
                </div>
              </div>

              {activeStage.is_locked && (
                <div className="case-stage-lock-tip">
                  当前阶段尚未解锁，请先完成并确认前一阶段。
                </div>
              )}

              {activeStage.key !== "cases" && (
                <>
                  <div className="case-result-header">
                    <label className="case-stage-label">阶段结果</label>
                    <div className="case-result-tabs">
                      <button
                        type="button"
                        className={activeView === "text" ? "review-comment-tab active" : "review-comment-tab"}
                        onClick={() => setActiveView("text")}
                      >
                        文本
                      </button>
                      <button
                        type="button"
                        className={activeView === "xmind" ? "review-comment-tab active" : "review-comment-tab"}
                        onClick={() => setActiveView("xmind")}
                      >
                        思维导图
                      </button>
                    </div>
                  </div>
                  {activeView === "text" ? (
                    <textarea
                      className="case-stage-content"
                      value={activeDraft.content}
                      onChange={(event) => patchDraft(activeStage.key, { content: event.target.value })}
                      readOnly={!canEdit}
                      placeholder="这里会显示当前阶段的生成结果，也可以人工补充。"
                    />
                  ) : (
                    <div className="case-mindmap-wrap">
                      <MindmapEditor
                        title={activeStage.title}
                        content={activeDraft.content}
                        editable={canEdit}
                        onChange={(nextContent) => patchDraft(activeStage.key, { content: nextContent })}
                      />
                    </div>
                  )}

                  <label className="case-stage-label">人工补充提示词</label>
                  <textarea
                    className="case-stage-prompt"
                    value={activeDraft.prompt}
                    onChange={(event) => patchDraft(activeStage.key, { prompt: event.target.value })}
                    readOnly={!canEdit}
                    placeholder="可以补充额外提示词，让模型重新生成更贴近期望的结果。"
                  />

                  {activeStage.template_content && (
                    <>
                      <label className="case-stage-label">{`阶段系统提示词${activeStage.template_name ? `（${activeStage.template_name}）` : ""}`}</label>
                      <textarea className="case-stage-prompt" value={activeStage.template_content} readOnly />
                    </>
                  )}

                  {canEdit && (
                    <div className="case-stage-footer">
                      <button type="button" className="btn ghost" onClick={saveDraft} disabled={submitting}>
                        保存
                      </button>
                      <button type="button" className="btn ghost" onClick={regenerateStage} disabled={submitting}>
                        {getRegenerateLabel(activeStage)}
                      </button>
                      <button type="button" className="btn action" onClick={confirmStage} disabled={submitting}>
                        确认并继续
                      </button>
                    </div>
                  )}
                </>
              )}

              {activeStage.key === "cases" && (
                <div className="case-generation-panel">
                  <div className="case-generation-controls">
                    <div className="case-generation-row">
                      <label className="case-stage-label required-inline">测试类型</label>
                      <div className="case-check-group">
                        {caseTypeOptions.map((item) => (
                          <label key={item.key} className={activeDraft.case_types?.includes(item.key) ? "case-check-chip active" : "case-check-chip"}>
                            <input
                              type="checkbox"
                              checked={activeDraft.case_types?.includes(item.key)}
                              onChange={() => toggleCaseType(item.key)}
                              disabled={!canEdit}
                            />
                            <span>{item.value}</span>
                          </label>
                        ))}
                      </div>
                    </div>

                    <div className="case-generation-row">
                      <label className="case-stage-label">知识库</label>
                      <div className="case-kb-section">
                        <div className="case-kb-dropdown">
                          <button
                            type="button"
                            className={kbDropdownOpen ? "case-kb-dropdown-trigger active" : "case-kb-dropdown-trigger"}
                            onClick={() => setKbDropdownOpen((prev) => !prev)}
                            disabled={!canEdit}
                          >
                            <span className={activeDraft.knowledge_bases?.length ? "case-kb-dropdown-value" : "case-kb-dropdown-value placeholder"}>
                              {knowledgeBaseLabel}
                            </span>
                            <span className="case-kb-dropdown-tools">
                              {activeDraft.knowledge_bases?.length > 0 && (
                                <span
                                  className="case-kb-dropdown-clear"
                                  onClick={clearKnowledgeBases}
                                  role="button"
                                  tabIndex={0}
                                >
                                  ×
                                </span>
                              )}
                              <span className="case-kb-dropdown-arrow">{kbDropdownOpen ? "▲" : "▼"}</span>
                            </span>
                          </button>
                          {kbDropdownOpen && (
                            <div className="case-kb-dropdown-menu">
                              <div className="case-kb-dropdown-hint">支持多选，点击右侧 × 可清空选择</div>
                              {knowledgeBaseOptions.map((item) => (
                                <label
                                  key={item}
                                  className={activeDraft.knowledge_bases?.includes(item) ? "case-kb-option active" : "case-kb-option"}
                                >
                                  <input
                                    type="checkbox"
                                    checked={activeDraft.knowledge_bases?.includes(item)}
                                    onChange={() => toggleKnowledgeBase(item)}
                                    disabled={!canEdit}
                                  />
                                  <span>{item}</span>
                                </label>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>

                    <label className="case-stage-label">人工补充提示词</label>
                    <textarea
                      className="case-stage-prompt"
                      value={activeDraft.prompt}
                      onChange={(event) => patchDraft(activeStage.key, { prompt: event.target.value })}
                      readOnly={!canEdit}
                      placeholder="可以在这里补充额外提示词，让模型在当前阶段重新生成更贴近你的结果。"
                    />

                    <div className="case-generation-actions">
                      <button type="button" className="btn ghost" onClick={addCase} disabled={!canEdit || submitting}>
                        新增用例
                      </button>
                      <button type="button" className="btn ghost" onClick={regenerateStage} disabled={!canEdit || submitting}>
                        生成/重新生成用例
                      </button>
                      <button type="button" className="btn action" onClick={saveDraft} disabled={!canEdit || submitting}>
                        保存用例
                      </button>
                    </div>
                  </div>

                  <div className="case-list-shell">
                    <div className="case-list-scroll">
                      <table className="case-edit-table">
                        <thead>
                          <tr>
                            <th>序号</th>
                            <th>测试点</th>
                            <th>用例名称</th>
                            <th>前置条件</th>
                            <th>测试步骤</th>
                            <th>预期结果</th>
                            <th>优先级</th>
                            <th>测试类型</th>
                            <th>操作</th>
                          </tr>
                        </thead>
                        <tbody>
                          {caseRows.length === 0 && (
                            <tr>
                              <td colSpan="9" className="empty">暂无用例，请先点击“生成/重新生成用例”或手动新增。</td>
                            </tr>
                          )}
                          {caseRows.map((item, index) => (
                            <tr key={`case-row-${index}`}>
                              <td>{index + 1}</td>
                              <td>
                                <textarea
                                  className="case-cell-textarea compact"
                                  value={item.test_point || ""}
                                  onChange={(event) => updateCase(index, { test_point: event.target.value })}
                                  readOnly={!canEdit}
                                />
                              </td>
                              <td>
                                <textarea
                                  className="case-cell-textarea compact"
                                  value={item.title || ""}
                                  onChange={(event) => updateCase(index, { title: event.target.value })}
                                  readOnly={!canEdit}
                                />
                              </td>
                              <td>
                                <textarea
                                  className="case-cell-textarea"
                                  value={formatLines(item.preconditions)}
                                  onChange={(event) => updateCase(index, { preconditions: parseLines(event.target.value) })}
                                  readOnly={!canEdit}
                                />
                              </td>
                              <td>
                                <textarea
                                  className="case-cell-textarea"
                                  value={formatLines(item.steps)}
                                  onChange={(event) => updateCase(index, { steps: parseLines(event.target.value) })}
                                  readOnly={!canEdit}
                                />
                              </td>
                              <td>
                                <textarea
                                  className="case-cell-textarea"
                                  value={formatLines(item.expected)}
                                  onChange={(event) => updateCase(index, { expected: parseLines(event.target.value) })}
                                  readOnly={!canEdit}
                                />
                              </td>
                              <td>
                                <select
                                  value={item.priority || ""}
                                  onChange={(event) => updateCase(index, { priority: event.target.value })}
                                  disabled={!canEdit}
                                >
                                  <option value="">请选择优先级</option>
                                  {casePriorityOptions.map((priority) => (
                                    <option key={priority.key} value={priority.key}>
                                      {`${priority.key} - ${priority.value}`}
                                    </option>
                                  ))}
                                </select>
                              </td>
                              <td>
                              <select
                                value={item.case_type || ""}
                                onChange={(event) => updateCase(index, { case_type: event.target.value })}
                                disabled={!canEdit}
                              >
                                <option value="">请选择用例类型</option>
                                {Array.from(new Set([
                                  ...(activeDraft.case_types?.length ? activeDraft.case_types : caseTypeOptions.map((type) => type.key)),
                                  item.case_type || "",
                                ].filter(Boolean))).map((type) => (
                                  <option key={type} value={type}>{CASE_TYPE_LABEL_MAP[type] || type}</option>
                                ))}
                              </select>
                              </td>
                              <td>
                                <div className="case-row-actions">
                                  <button type="button" className="link" onClick={() => duplicateCase(index)} disabled={!canEdit}>复制</button>
                                  <button type="button" className="link link-danger" onClick={() => deleteCase(index)} disabled={!canEdit}>删除</button>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {activeStage.template_content && (
                    <>
                      <label className="case-stage-label">{`阶段系统提示词${activeStage.template_name ? `（${activeStage.template_name}）` : ""}`}</label>
                      <textarea className="case-stage-prompt" value={activeStage.template_content} readOnly />
                    </>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </section>
  );
}

