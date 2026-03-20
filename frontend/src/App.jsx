import React, { useEffect, useMemo, useRef, useState } from "react";

import {

  ASSET_BASE_URL,

  bulkDeleteRequirements,

  createTestCase,

  createTestCaseModule,

  createProject,

  deleteTestCaseModule,

  deleteTestCase,

  deleteRequirement,

  deleteProject,

  getDictionaries,

  getHealth,

  getProjects,

  getRequirementImportConfig,

  getRequirementPreview,

  getRequirementReviews,

  getReviewChecks,

  getRequirements,

  getReviewRun,

  getReviewRunStatus,

  getTestCaseModules,

  getTestCaseSidebar,

  getTestCases,

  importRequirement,

  startRequirementReview,

  updateTestCaseModule,

  updateTestCase,

  updateProject,

} from "./api";

import LlmConfigPage from "./LlmConfigPage";

import PromptManagementPage from "./PromptManagementPage";

import TestCaseWorkflowPage from "./TestCaseWorkflowPage";

import StandaloneCaseGeneratorPage from "./StandaloneCaseGeneratorPage";

import "./styles.css";



const MODULES = {

  projects: "项目管理",

  requirements: "需求管理",

  cases: "用例管理",

  llmConfigs: "LLM配置",

  prompts: "提示词管理",

};



const REVIEW_OPTIONS = ["可测性分析", "可行性分析", "逻辑分析", "清晰度分析"];

const CASE_SIDEBAR_TEXT = {
  searchPlaceholder: "??????",
  add: "??",
  allPrefix: "??",
  empty: "????",
};

const ALL_CHECK_KEY = "全部";



const ANALYSIS_CLASS_MAP = {

  "可测性分析": "analysis-testability",

  "可行性分析": "analysis-feasibility",

  "逻辑分析": "analysis-logic",

  "清晰度分析": "analysis-clarity",

};



const DEFAULT_FILTERS = {

  start_date: "",

  end_date: "",

  project_id: "",

  review_status: "",

  creator: "",

  keyword: "",

  page: 1,

  page_size: 10,

};



const DEFAULT_PROJECT_FILTERS = {

  keyword: "",

  page: 1,

  page_size: 10,

};



const DEFAULT_PROJECT_FORM = {

  name: "",

  description: "",

  creator: "admin",

};



const DEFAULT_IMPORT_FORM = {

  project_id: "",

  title: "",

  creator: "admin",

  import_method: "file",

  jira_url: "",

  status: "草稿",

  summary: "",

};



const MANUAL_CASE_REQUIREMENT_ID = "manual_case_root";



const DEFAULT_CASE_TYPE_OPTIONS = [

  { key: "functional", value: "功能测试" },

  { key: "boundary", value: "边界测试" },

  { key: "exception", value: "异常测试" },

  { key: "permission", value: "权限测试" },

  { key: "security", value: "安全测试" },

  { key: "compatibility", value: "兼容性测试" },

  { key: "smoke", value: "冒烟测试" },

];

const DEFAULT_CASE_PRIORITY_OPTIONS = [

  { key: "P0", value: "高级" },

  { key: "P1", value: "中级" },

  { key: "P2", value: "低级" },

  { key: "P3", value: "最低级" },

];

const CASE_STAGE_OPTIONS = ["需求分析", "开发中", "提测", "回归测试", "验收测试"];

const CASE_EXPORT_FIELD_COLUMNS = [

  { key: "test_point", label: "测试点" },

  { key: "title", label: "用例名称" },

  { key: "priority_label", label: "优先级" },

  { key: "case_type", label: "测试类型" },

  { key: "module_name", label: "所属模块" },

  { key: "creator", label: "创建者" },

  { key: "created_at", label: "创建时间" },

  { key: "system_name", label: "所属系统" },

  { key: "requirement_no", label: "需求编号" },

  { key: "requirement_name", label: "需求名称" },

  { key: "preconditions_text", label: "前置条件" },

  { key: "steps_text", label: "测试步骤" },

  { key: "expected_text", label: "预期结果" },

  { key: "stage", label: "适用阶段" },

];

const CASE_EXPORT_FIELD_LABEL_MAP = Object.fromEntries(CASE_EXPORT_FIELD_COLUMNS.map((item) => [item.key, item.label]));

const CASE_EXPORT_DEFAULT_FIELDS = {

  excel: [

    "system_name",

    "module_name",

    "requirement_no",

    "requirement_name",

    "title",

    "preconditions_text",

    "steps_text",

    "expected_text",

    "priority_label",

    "case_type",

    "stage",

  ],

  word: [

    "title",

    "case_type",

    "priority_label",

    "preconditions_text",

    "test_point",

    "steps_text",

    "expected_text",

    "actual_result",

    "test_status",

  ],

};

const CASE_EXPORT_STYLE_PRESETS = {

  excel: {

    titleText: "用例导出",

    titleColor: "#111827",

    metaColor: "#475569",

    headerBg: "#37379b",

    headerText: "#ffffff",

    borderColor: "#2f3075",

    bodyText: "#111827",

    titleSize: 20,

    headerSize: 12,

    bodySize: 12,

  },

  word: {

    titleText: "测试用例",

    titleColor: "#1d63d8",

    metaColor: "#475569",

    headerBg: "#d9d9d9",

    headerText: "#111827",

    borderColor: "#333333",

    bodyText: "#111827",

    titleSize: 28,

    headerSize: 12,

    bodySize: 12,

  },

};

const CASE_EXPORT_RICH_FIELDS = new Set(["preconditions_text", "steps_text", "expected_text", "test_point"]);

const CASE_EXPORT_SAMPLE_ROW = {

  serial: 1,

  system_name: "\u8239\u8236\u9884\u8b66\u7cfb\u7edf",

  module_name: "\u7efc\u5408\u6a21\u578b\u6a21\u5757",

  requirement_no: "REQ-138",

  requirement_name: "\u7efc\u5408\u6a21\u578b\u6a21\u677f\u7f16\u8f91",

  title: "\u7efc\u5408\u6a21\u578b\u6a21\u677f\u7f16\u8f91",

  preconditions_text: "1. \u53cc\u53cd\u6253\u79c1\u8d26\u53f7\u767b\u5f55",

  steps_text: `1. \u8fdb\u5165\u6a21\u5757\u7ba1\u7406-\u7efc\u5408\u6a21\u578b\u6a21\u677f

2. \u6253\u5f00\u76ee\u6807\u6a21\u677f\u5e76\u70b9\u51fb\u7f16\u8f91

3. \u4fee\u6539\u6a21\u677f\u5185\u5bb9\u540e\u70b9\u51fb\u4fdd\u5b58`,

  expected_text: `1. \u9875\u9762\u5c55\u793a\u6a21\u677f\u5217\u8868

2. \u53ef\u8fdb\u5165\u7f16\u8f91\u72b6\u6001

3. \u4fdd\u5b58\u6210\u529f\u5e76\u63d0\u793a\u7ed3\u679c`,

  priority_label: "\u9ad8\u7ea7",

  case_type: "\u529f\u80fd\u7528\u4f8b",

  stage: "\u56de\u5f52\u6d4b\u8bd5",

  test_point: "\u53cc\u53cd\u6253\u79c1\u8d26\u53f7\u767b\u5f55",

  actual_result: "",

  test_status: "\u901a\u8fc7",

};

function cloneCaseExportStyle(format) {

  return { ...CASE_EXPORT_STYLE_PRESETS[format] };

}

function getDefaultCaseExportFields(format) {

  return [...CASE_EXPORT_DEFAULT_FIELDS[format]];

}



function createCaseStep(index = 1) {

  return {

    id: `step-${Date.now()}-${index}-${Math.random().toString(16).slice(2, 8)}`,

    step: "",

    expected: "",

  };

}



function createEmptyCaseForm(requirementId = "", moduleId = "") {

  return {

    requirement_id: requirementId,

    module_id: moduleId,

    case_type: "functional",

    stage: "",

    title: "",

    test_point: "",

    preconditions_text: "",

    priority: "P2",

    creator: "admin",

    steps: [createCaseStep(1), createCaseStep(2), createCaseStep(3)],

  };

}



function escapeRegExp(value) {

  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

}



function escapeHtml(value) {

  return value

    .replaceAll("&", "&amp;")

    .replaceAll("<", "&lt;")

    .replaceAll(">", "&gt;")

    .replaceAll('"', "&quot;")

    .replaceAll("'", "&#39;");

}



function getAnalysisClass(name) {

  return ANALYSIS_CLASS_MAP[name] || "analysis-default";

}



function getReviewStatusLabel(status) {

  if (!status || status === "待评审") return "未开始";

  if (status === "评审中") return "进行中";

  if (status === "评审完成") return "已完成";

  return status;

}



function formatFilterDateTime(value) {

  if (!value) return "";

  return value.replace("T", " ");

}



function getFilterSeconds(field) {

  return field === "end_date" ? "59" : "00";

}



function normalizeManualDateTime(value, field) {

  const raw = value.trim();

  if (!raw) return "";

  const match = raw.match(/^(\d{4})[-\/](\d{1,2})[-\/](\d{1,2})(?:\s+(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?)?$/);

  if (!match) return null;

  const [, year, month, day, hour = "00", minute = "00", second = getFilterSeconds(field)] = match;

  const safeMonth = String(month).padStart(2, "0");

  const safeDay = String(day).padStart(2, "0");

  const safeHour = String(hour).padStart(2, "0");

  const safeMinute = String(minute).padStart(2, "0");

  const safeSecond = String(second).padStart(2, "0");

  return `${year}-${safeMonth}-${safeDay} ${safeHour}:${safeMinute}:${safeSecond}`;

}



function splitDateTime(value) {

  if (!value) return { date: "", time: "" };

  const normalized = value.replace("T", " ");

  const [date = "", time = ""] = normalized.split(" ");

  return { date, time: time.slice(0, 5) };

}



function combineDateTime(date, time, field) {

  if (!date) return "";

  return `${date} ${time || "00:00"}:${getFilterSeconds(field)}`;

}



function getPanelBaseDate(value) {

  if (value) {

    const parsed = new Date(value);

    if (!Number.isNaN(parsed.getTime())) return parsed;

  }

  return new Date();

}



function getPanelMonthState(value) {

  const base = getPanelBaseDate(value);

  return { year: base.getFullYear(), month: base.getMonth() };

}



function formatPanelMonth(year, month) {

  return `${year}年${month + 1}月`;

}



function getCalendarDays(year, month) {

  const firstDay = new Date(year, month, 1);

  const startWeekDay = (firstDay.getDay() + 6) % 7;

  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const daysInPrevMonth = new Date(year, month, 0).getDate();

  const cells = [];



  for (let i = startWeekDay - 1; i >= 0; i -= 1) {

    cells.push({ day: daysInPrevMonth - i, currentMonth: false, date: new Date(year, month - 1, daysInPrevMonth - i) });

  }

  for (let day = 1; day <= daysInMonth; day += 1) {

    cells.push({ day, currentMonth: true, date: new Date(year, month, day) });

  }

  while (cells.length < 42) {

    const nextDay = cells.length - (startWeekDay + daysInMonth) + 1;

    cells.push({ day: nextDay, currentMonth: false, date: new Date(year, month + 1, nextDay) });

  }

  return cells;

}



function formatDateValue(date) {

  const year = date.getFullYear();

  const month = String(date.getMonth() + 1).padStart(2, "0");

  const day = String(date.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;

}



function isSameDate(dateA, dateB) {

  return !!dateA && !!dateB && dateA === dateB;

}



const WEEKDAY_LABELS = ["一", "二", "三", "四", "五", "六", "日"];

const HOUR_OPTIONS = Array.from({ length: 24 }, (_, index) => String(index).padStart(2, "0"));

const MINUTE_OPTIONS = Array.from({ length: 60 }, (_, index) => String(index).padStart(2, "0"));



function buildAnnotatedHtml(requirement, annotations) {

  if (!requirement) return "";

  const orderMap = Object.fromEntries(annotations.map((annotation, index) => [annotation.id, index + 1]));

  const sorted = [...annotations].sort((a, b) => b.quote.length - a.quote.length);



  if (requirement.preview_type === "html") {

    let content = requirement.preview_html || "";

    sorted.forEach((annotation, index) => {

      const order = orderMap[annotation.id] || 0;

      const badge = `<span class="doc-note-tag ${getAnalysisClass(annotation.comment_title)}">${order}</span>`;

      const replacement = `<mark class="doc-highlight ${getAnalysisClass(annotation.comment_title)}" data-annotation-id="${annotation.id}">${annotation.quote}${badge}</mark>`;

      content = content.replace(annotation.quote, replacement);

    });

    return content;

  }



  let text = escapeHtml(requirement.body_text || requirement.content || "").replaceAll("\n", "<br />");

  sorted.forEach((annotation, index) => {

    const order = orderMap[annotation.id] || 0;

    const badge = `<span class="doc-note-tag ${getAnalysisClass(annotation.comment_title)}">${order}</span>`;

    const regex = new RegExp(escapeRegExp(escapeHtml(annotation.quote)), "g");

    text = text.replace(regex, `<mark class="doc-highlight ${getAnalysisClass(annotation.comment_title)}" data-annotation-id="${annotation.id}">${escapeHtml(annotation.quote)}${badge}</mark>`);

  });

  return `<div class="docx-preview">${text}</div>`;

}



function buildSummaryRemark(currentRun) {

  const results = currentRun?.results || [];

  const checks = currentRun?.checks || [];



  if (!currentRun) return null;



  const score = results.length

    ? Math.round(results.reduce((sum, item) => sum + (item.score || 0), 0) / results.length)

    : 0;



  const level = score >= 85 ? "优秀" : score >= 75 ? "良好" : score >= 60 ? "一般" : "需完善";

  const strongResults = results.filter((item) => (item.score || 0) >= 80);

  const strengths = strongResults.length > 0

    ? strongResults.slice(0, 3).map((item) => `${item.name}较完整，${item.summary || "当前描述对该维度已有较明确支撑。"}`)

    : results.length > 0

      ? ["需求主线已经存在，目标和主要场景基本可识别。"]

      : ["开始评审后，这里会提炼这份需求描述已经具备的优点。"];

  const weaknessList = results.flatMap((item) => item.findings || []).filter(Boolean);

  const improvements = weaknessList.length > 0

    ? weaknessList.slice(0, 3)

    : results.map((item) => item.suggestion).filter(Boolean).slice(0, 3);

  const normalizedImprovements = improvements.length > 0

    ? improvements

    : ["建议补充验收标准、边界条件和异常处理，便于产品、开发、测试形成一致理解。"];



  const oneLineSummary = results.length

    ? `已完成 ${results.length}/${checks.length} 个评审项，当前需求整体${level}。优点集中在主流程和目标描述已有基础，短板主要在约束条件、验收口径和异常路径还不够具体。`

    : `当前已选择 ${checks.length} 个评审项，评审开始后会在这里提炼优点、缺点和改进方向。`;



  return {

    id: `summary-${currentRun.id}`,

    score,

    level,

    headline: "总体评价",

    oneLineTitle: "一句话总结",

    oneLineSummary,

    strengthsTitle: "当前做得好的点",

    strengths,

    improvementsTitle: "优先需要补充的点",

    improvements: normalizedImprovements,

  };

}

function App() {

  const [health, setHealth] = useState("checking");

  const [error, setError] = useState("");

  const [openTabs, setOpenTabs] = useState([{ key: "projects", label: "项目管理", type: "module" }]);

  const [activeTabKey, setActiveTabKey] = useState("projects");



  const [projects, setProjects] = useState([]);

  const [projectTotal, setProjectTotal] = useState(0);

  const [projectFilters, setProjectFilters] = useState(DEFAULT_PROJECT_FILTERS);

  const [showProjectModal, setShowProjectModal] = useState(false);

  const [editingProjectId, setEditingProjectId] = useState("");

  const [projectForm, setProjectForm] = useState(DEFAULT_PROJECT_FORM);



  const [requirements, setRequirements] = useState([]);

  const [reqTotal, setReqTotal] = useState(0);

  const [reqFilters, setReqFilters] = useState(DEFAULT_FILTERS);

  const [selectedIds, setSelectedIds] = useState([]);

  const [showReqImportModal, setShowReqImportModal] = useState(false);

  const [showPreviewModal, setShowPreviewModal] = useState(false);

  const [reqImportForm, setReqImportForm] = useState(DEFAULT_IMPORT_FORM);

  const [reqImportFile, setReqImportFile] = useState(null);

  const [importConfig, setImportConfig] = useState({ upload_extensions: [], sources: {} });

  const [previewData, setPreviewData] = useState(null);

  const [activeDatePanel, setActiveDatePanel] = useState("");

  const [dateDrafts, setDateDrafts] = useState({ start_date: { date: "", time: "" }, end_date: { date: "", time: "" } });

  const [datePanelMonths, setDatePanelMonths] = useState({ start_date: getPanelMonthState(""), end_date: getPanelMonthState("") });

  const [dateInputTexts, setDateInputTexts] = useState({ start_date: "", end_date: "" });



  const [reviewStates, setReviewStates] = useState({});

  const [reviewCommentModes, setReviewCommentModes] = useState({});

  const [reviewSelectOpenId, setReviewSelectOpenId] = useState("");

  const [activeAnnotationIds, setActiveAnnotationIds] = useState({});

  const reviewDocumentRefs = useRef({});

  const reviewCommentRefs = useRef({});

  const reviewSelectRefs = useRef({});

  const datePanelRefs = useRef({});

  const [caseCount, setCaseCount] = useState(0);

  const [reviewOptions, setReviewOptions] = useState(REVIEW_OPTIONS);

  const [testCases, setTestCases] = useState([]);

  const [caseModules, setCaseModules] = useState([]);

  const [caseSidebarData, setCaseSidebarData] = useState({ all_count: 0, linked_count: 0, module_tree: [], requirement_tree: { id: "requirement-root", name: "需求类", count: 0, children: [] } });

  const [caseFilters, setCaseFilters] = useState({ keyword: "", priority: "", caseType: "" });

  const [caseKeywordInput, setCaseKeywordInput] = useState("");

  const [casePagination, setCasePagination] = useState({ page: 1, page_size: 10 });

  const [caseModuleKeyword, setCaseModuleKeyword] = useState("");

  const [caseModuleKeywordInput, setCaseModuleKeywordInput] = useState("");

  const [selectedCaseScope, setSelectedCaseScope] = useState({ kind: "all", value: "" });

  const [caseEditorMode, setCaseEditorMode] = useState("list");

  const [editingCaseId, setEditingCaseId] = useState("");

  const [caseForm, setCaseForm] = useState(createEmptyCaseForm());

  const [caseTypeDicts, setCaseTypeDicts] = useState([]);

  const [casePriorityDicts, setCasePriorityDicts] = useState([]);

  const [showCaseModuleModal, setShowCaseModuleModal] = useState(false);

  const [caseModuleForm, setCaseModuleForm] = useState({ parent_id: "", name: "" });

  const [editingCaseModuleId, setEditingCaseModuleId] = useState("");

  const [expandedCaseModuleIds, setExpandedCaseModuleIds] = useState({});

  const [caseSidebarCollapsed, setCaseSidebarCollapsed] = useState(false);

  const [showCaseExportModal, setShowCaseExportModal] = useState(false);

  const [caseExportFormat, setCaseExportFormat] = useState("excel");

  const [caseExportFields, setCaseExportFields] = useState(getDefaultCaseExportFields("excel"));

  const [caseExportStyle, setCaseExportStyle] = useState(() => cloneCaseExportStyle("excel"));

  const [showCaseExportFieldMenu, setShowCaseExportFieldMenu] = useState(false);

  const [draggingCaseExportField, setDraggingCaseExportField] = useState("");

  const [exportingCases, setExportingCases] = useState(false);



  const projectMap = useMemo(() => Object.fromEntries(projects.map((item) => [item.id, item])), [projects]);

  const activeTab = openTabs.find((tab) => tab.key === activeTabKey) || openTabs[0];

  const requirementOptions = useMemo(

    () => requirements.map((item) => ({ id: item.id, label: item.title || item.summary || item.id })),

    [requirements]

  );

  const caseModuleMap = useMemo(() => Object.fromEntries(caseModules.map((item) => [item.id, item])), [caseModules]);

  const requirementMap = useMemo(() => Object.fromEntries(requirements.map((item) => [item.id, item])), [requirements]);

  const requirementCaseTargets = useMemo(

    () =>

      requirements

        .filter((item) => !item.hidden)

        .map((item) => ({

          key: `req:${item.id}`,

          label: `${item.project || projectMap[item.project_id]?.name || "未分组项目"} / ${item.title || item.summary || item.id}`,

          requirementId: item.id,

          moduleId: "",

          group: "需求类",

        })),

    [projectMap, requirements]

  );

  const customCaseTargets = useMemo(

    () =>

      caseModules.map((item) => ({

        key: `module:${item.id}`,

        label: item.name,

        requirementId: "",

        moduleId: item.id,

        group: "自定义分组",

      })),

    [caseModules]

  );

  const caseTargetOptions = useMemo(() => [...requirementCaseTargets, ...customCaseTargets], [customCaseTargets, requirementCaseTargets]);

  const caseTypeOptions = useMemo(

    () => (caseTypeDicts.length ? caseTypeDicts : DEFAULT_CASE_TYPE_OPTIONS),

    [caseTypeDicts]

  );

  const casePriorityOptions = useMemo(

    () => (casePriorityDicts.length ? casePriorityDicts : DEFAULT_CASE_PRIORITY_OPTIONS),

    [casePriorityDicts]

  );

  const casePriorityLabelMap = useMemo(

    () => Object.fromEntries(casePriorityOptions.map((item) => [item.key, item.value])),

    [casePriorityOptions]

  );

  const filteredModuleOptions = useMemo(() => {

    const keyword = caseModuleKeyword.trim().toLowerCase();

    if (!keyword) return caseModules;

    return caseModules.filter((item) => item.name.toLowerCase().includes(keyword));

  }, [caseModuleKeyword, caseModules]);

  const currentCaseQuery = useMemo(() => {

    const query = {

      keyword: caseFilters.keyword,

      priority: caseFilters.priority,

      case_type: caseFilters.caseType,

      page: casePagination.page,

      page_size: casePagination.page_size,

    };

    if (selectedCaseScope.kind === "module") query.module_id = selectedCaseScope.value;

    if (selectedCaseScope.kind === "requirement") query.requirement_id = selectedCaseScope.value;

    if (selectedCaseScope.kind === "project") {

      query.project_id = selectedCaseScope.value;

      query.linked_only = true;

    }

    if (selectedCaseScope.kind === "requirement_root") {

      query.linked_only = true;

    }

    return query;

  }, [caseFilters.caseType, caseFilters.keyword, caseFilters.priority, casePagination.page, casePagination.page_size, selectedCaseScope]);



  async function runSafe(task) {

    try {

      setError("");

      await task();

    } catch (e) {

      setError(e.message || "请求失败");

    }

  }



  async function loadProjects(overrides = {}) {

    const params = { ...projectFilters, ...overrides };

    const res = await getProjects(params);

    setProjects(res.items || []);

    setProjectTotal(res.total || 0);

    setProjectFilters((prev) => ({ ...prev, ...overrides }));

  }



  async function loadRequirements(overrides = {}) {

    const params = { ...reqFilters, ...overrides };

    const res = await getRequirements(params);

    setRequirements(res.items || []);

    setReqTotal(res.total || 0);

    setReqFilters((prev) => ({ ...prev, ...overrides }));

    setSelectedIds([]);

  }



  async function loadTestCases(overrides = {}) {

    const params = { ...currentCaseQuery, ...overrides };

    const result = await getTestCases(params);

    setTestCases(result.items || []);

    setCaseCount(result.total || 0);

    setCasePagination((prev) => ({

      ...prev,

      page: result.page || params.page || prev.page,

      page_size: result.page_size || params.page_size || prev.page_size,

    }));

  }



  async function loadCaseModules() {

    const items = await getTestCaseModules();

    setCaseModules(items || []);

    setExpandedCaseModuleIds((prev) => {

      const next = { ...prev };

      (items || []).forEach((item) => {

        if (next[item.id] === undefined) next[item.id] = true;

      });

      return next;

    });

  }



  async function loadCaseSidebar() {

    const result = await getTestCaseSidebar();

    setCaseSidebarData(result || { all_count: 0, linked_count: 0, module_tree: [], requirement_tree: { id: "requirement-root", name: "需求类", count: 0, children: [] } });

    setExpandedCaseModuleIds((prev) => {

      const next = { ...prev };

      const visit = (nodes = []) => {

        nodes.forEach((node) => {

          if (next[node.id] === undefined) next[node.id] = true;

          visit(node.children || []);

        });

      };

      visit(result?.module_tree || []);

      const requirementChildren = result?.requirement_tree?.children || [];

      visit(requirementChildren);

      return next;

    });

  }



  async function loadCounts() {

    await loadTestCases();

  }



  async function loadReviewChecks() {

    const result = await getReviewChecks();

    const items = (result.items || []).map((item) => item.name).filter(Boolean);

    setReviewOptions(items);

    return items;

  }



  async function loadCaseDictionaries() {

    const [typeResult, priorityResult] = await Promise.all([

      getDictionaries("case_type"),

      getDictionaries("case_priority"),

    ]);

    setCaseTypeDicts(typeResult.items || []);

    setCasePriorityDicts(priorityResult.items || []);

  }



  useEffect(() => {

    getHealth().then((res) => setHealth(res.status)).catch(() => setHealth("down"));

    runSafe(async () => {

      await loadProjects();

      await loadRequirements();

      await loadCounts();

      await loadCaseModules();

      await loadCaseSidebar();

      await loadReviewChecks();

      await loadCaseDictionaries();

      setImportConfig(await getRequirementImportConfig());

    });

  }, []);



  useEffect(() => {

    if (activeTab?.key !== "cases") return;

    runSafe(async () => {

      await loadCaseModules();

      await loadCaseSidebar();

      await loadTestCases();

    });

  }, [activeTab?.key, currentCaseQuery]);



  useEffect(() => {

    setCasePagination((prev) => (prev.page === 1 ? prev : { ...prev, page: 1 }));

  }, [caseFilters.caseType, caseFilters.keyword, caseFilters.priority, selectedCaseScope]);



  useEffect(() => {

    setDateInputTexts({

      start_date: formatFilterDateTime(reqFilters.start_date),

      end_date: formatFilterDateTime(reqFilters.end_date),

    });

  }, [reqFilters.start_date, reqFilters.end_date]);



  useEffect(() => {

    if (!activeTab || activeTab.type != "review") return undefined;

    const requirementId = activeTab.requirementId;

    const state = reviewStates[requirementId];

    const currentRun = state?.runs?.find((item) => item.id === state.currentRunId) || state?.runs?.[0];

    const annotations = currentRun?.results?.flatMap((item) => item.annotations || []) || [];

    if (annotations.length === 0) return undefined;



    setActiveAnnotationIds((prev) => {

      if (prev[requirementId]) return prev;

      return { ...prev, [requirementId]: annotations[0].id };

    });

    return undefined;

  }, [activeTab, reviewStates]);



  useEffect(() => {

    function handlePointerDown(event) {

      if (activeDatePanel) {

        const panelNode = datePanelRefs.current[activeDatePanel];

        if (!(panelNode && panelNode.contains(event.target))) {

          setActiveDatePanel("");

        }

      }



      if (reviewSelectOpenId) {

        const selectNode = reviewSelectRefs.current[reviewSelectOpenId];

        if (!(selectNode && selectNode.contains(event.target))) {

          setReviewSelectOpenId("");

        }

      }

    }



    document.addEventListener("mousedown", handlePointerDown);

    return () => document.removeEventListener("mousedown", handlePointerDown);

  }, [activeDatePanel, reviewSelectOpenId]);



  useEffect(() => {

    if (!activeTab || activeTab.type !== "review") return undefined;

    const requirementId = activeTab.requirementId;

    const state = reviewStates[requirementId];

    const run = state?.runs.find((item) => item.id === state.currentRunId);

    if (!run || run.status !== "running") return undefined;



    const timer = setInterval(() => {

      runSafe(async () => {

        const latest = await getReviewRun(run.id);

        setReviewStates((prev) => {

          const current = prev[requirementId];

          if (!current) return prev;

          return {

            ...prev,

            [requirementId]: {

              ...current,

              requirement: {

                ...current.requirement,

                review_status: latest.status === "completed" ? "评审完成" : latest.status === "failed" ? "待评审" : "评审中",

              },

              runs: current.runs.map((item) => (item.id === latest.id ? latest : item)),

            },

          };

        });

        if (latest.status === "completed" || latest.status === "failed") {

          await loadRequirements();

        }

      });

    }, 1200);



    return () => clearInterval(timer);

  }, [activeTab, reviewStates]);



  function openModule(moduleKey) {

    if (!openTabs.find((tab) => tab.key === moduleKey)) {

      setOpenTabs((prev) => [...prev, { key: moduleKey, label: MODULES[moduleKey], type: "module" }]);

    }

    setActiveTabKey(moduleKey);

  }



  function closeTab(tabKey, event) {

    event.stopPropagation();

    if (openTabs.length === 1) return;

    const nextTabs = openTabs.filter((tab) => tab.key !== tabKey);

    setOpenTabs(nextTabs);

    if (activeTabKey === tabKey) {

      setActiveTabKey(nextTabs[nextTabs.length - 1].key);

    }

  }



  function openDatePicker(field) {

    setDateDrafts((prev) => ({ ...prev, [field]: splitDateTime(reqFilters[field]) }));

    setDatePanelMonths((prev) => ({ ...prev, [field]: getPanelMonthState(reqFilters[field]) }));

    setActiveDatePanel(field);

  }



  function clearDateFilter(field) {

    setReqFilters((prev) => ({ ...prev, [field]: "" }));

    setDateDrafts((prev) => ({ ...prev, [field]: { date: "", time: "" } }));

    setDateInputTexts((prev) => ({ ...prev, [field]: "" }));

    if (activeDatePanel === field) setActiveDatePanel("");

  }



  function updateDateDraft(field, key, value) {

    setDateDrafts((prev) => ({

      ...prev,

      [field]: {

        ...prev[field],

        [key]: value,

      },

    }));

  }



  function shiftPanelMonth(field, diff) {

    setDatePanelMonths((prev) => {

      const current = prev[field] || getPanelMonthState("");

      const nextDate = new Date(current.year, current.month + diff, 1);

      return {

        ...prev,

        [field]: { year: nextDate.getFullYear(), month: nextDate.getMonth() },

      };

    });

  }



  function selectDraftDate(field, dateValue) {

    setDateDrafts((prev) => ({

      ...prev,

      [field]: {

        ...prev[field],

        date: dateValue,

      },

    }));

  }



  function selectDraftHour(field, hour) {

    setDateDrafts((prev) => {

      const [, minute = "00"] = (prev[field]?.time || "00:00").split(":");

      return {

        ...prev,

        [field]: {

          ...prev[field],

          time: `${hour}:${minute}`,

        },

      };

    });

  }



  function selectDraftMinute(field, minute) {

    setDateDrafts((prev) => {

      const [hour = "00"] = (prev[field]?.time || "00:00").split(":");

      return {

        ...prev,

        [field]: {

          ...prev[field],

          time: `${hour}:${minute}`,

        },

      };

    });

  }



  function applyDateDraft(field) {

    const draft = dateDrafts[field] || { date: "", time: "" };

    const nextValue = combineDateTime(draft.date, draft.time, field);

    setReqFilters((prev) => ({ ...prev, [field]: nextValue }));

    setDateInputTexts((prev) => ({ ...prev, [field]: formatFilterDateTime(nextValue) }));

    setActiveDatePanel("");

  }



  function changeDateInputText(field, value) {

    setDateInputTexts((prev) => ({ ...prev, [field]: value }));

  }



  function commitDateInput(field) {

    const rawValue = dateInputTexts[field] || "";

    const normalized = normalizeManualDateTime(rawValue, field);

    if (normalized === null) {

      setDateInputTexts((prev) => ({ ...prev, [field]: formatFilterDateTime(reqFilters[field]) }));

      return;

    }

    setReqFilters((prev) => ({ ...prev, [field]: normalized }));

    setDateDrafts((prev) => ({ ...prev, [field]: splitDateTime(normalized) }));

    setDatePanelMonths((prev) => ({ ...prev, [field]: getPanelMonthState(normalized) }));

    setDateInputTexts((prev) => ({ ...prev, [field]: formatFilterDateTime(normalized) }));

  }



  function resetFilters() {

    runSafe(async () => {

      setReqFilters(DEFAULT_FILTERS);

      await loadRequirements(DEFAULT_FILTERS);

    });

  }



  function openProjectCreate() {

    setEditingProjectId("");

    setProjectForm(DEFAULT_PROJECT_FORM);

    setShowProjectModal(true);

  }



  function openProjectEdit(item) {

    setEditingProjectId(item.id);

      setProjectForm({ name: item.name, description: item.description, creator: item.creator || "" });

    setShowProjectModal(true);

  }



  async function submitProject() {

    await runSafe(async () => {

      if (editingProjectId) {

        await updateProject(editingProjectId, projectForm);

      } else {

        await createProject(projectForm);

      }

      setShowProjectModal(false);

      setProjectForm(DEFAULT_PROJECT_FORM);

      setEditingProjectId("");

      await loadProjects();

    });

  }



  async function removeProject(id) {

    await runSafe(async () => {

      await deleteProject(id);

      await loadProjects();

    });

  }



  function openImportModal() {

    setReqImportForm({ ...DEFAULT_IMPORT_FORM, project_id: projects[0]?.id || "" });

    setReqImportFile(null);

    setShowReqImportModal(true);

  }



  function toggleSelect(id) {

    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((v) => v !== id) : [...prev, id]));

  }



  function toggleSelectAll(checked) {

    setSelectedIds(checked ? requirements.map((item) => item.id) : []);

  }



  function handleImportFile(file) {

    setReqImportFile(file);

    if (!file) return;

    const stem = file.name.replace(/\.[^.]+$/, "");

    setReqImportForm((prev) => ({ ...prev, title: prev.title.trim() ? prev.title : stem }));

  }



  async function submitRequirementImport() {

    await runSafe(async () => {

      const formData = new FormData();

      Object.entries(reqImportForm).forEach(([key, value]) => formData.append(key, value ?? ""));

      if (reqImportForm.import_method === "file") {

        if (!reqImportFile) throw new Error("璇烽€夋嫨涓婁紶鏂囦欢");

        formData.append("file", reqImportFile);

      }

      await importRequirement(formData);

      setShowReqImportModal(false);

      setReqImportFile(null);

      setReqFilters(DEFAULT_FILTERS);

      setDateInputTexts({ start_date: "", end_date: "" });

      await loadRequirements(DEFAULT_FILTERS);

    });

  }



  async function removeRequirement(id) {

    await runSafe(async () => {

      await deleteRequirement(id);

      await loadRequirements();

    });

  }



  async function removeBatch() {

    if (selectedIds.length === 0) return;

    await runSafe(async () => {

      await bulkDeleteRequirements(selectedIds);

      await loadRequirements();

    });

  }



  async function openPreview(item) {

    await runSafe(async () => {

      const data = await getRequirementPreview(item.id);

      setPreviewData(data);

      setShowPreviewModal(true);

    });

  }



  async function openReviewPage(item) {

    const key = `review:${item.id}`;

    if (!openTabs.find((tab) => tab.key === key)) {

      setOpenTabs((prev) => [...prev, { key, label: `${item.title} 璇勫`, type: "review", requirementId: item.id }]);

    }

    setActiveTabKey(key);



    await runSafe(async () => {

      const [detail, history, reviewCheckResult] = await Promise.all([

        getRequirementPreview(item.id),

        getRequirementReviews(item.id),

        getReviewChecks(),

      ]);

      const runs = history.items || [];

      const nextReviewOptions = (reviewCheckResult.items || []).map((check) => check.name).filter(Boolean);

      setReviewOptions(nextReviewOptions);

      setReviewStates((prev) => {

        const previousSelected = prev[item.id]?.selectedChecks || [];

        const validSelected = previousSelected.filter((check) => nextReviewOptions.includes(check));

        return {

          ...prev,

          [item.id]: {

            requirement: detail,

            runs,

            currentRunId: runs[0]?.id || detail.latest_review_run_id || null,

            selectedChecks: validSelected.length > 0 ? validSelected : nextReviewOptions,

          },

        };

      });

    });

  }



  function openCaseWorkflowPage(item) {

    const key = `case-workflow:${item.id}`;

    if (!openTabs.find((tab) => tab.key === key)) {

      setOpenTabs((prev) => [...prev, { key, label: `${item.title} 用例`, type: "caseWorkflow", requirementId: item.id }]);

    }

    setActiveTabKey(key);

  }



  function getRequirementLabel(requirementId) {

    return requirementOptions.find((item) => item.id === requirementId)?.label || "";

  }



  function getModuleLabel(moduleId) {

    return caseModuleMap[moduleId]?.name || "";

  }



  function getCaseTargetValue(requirementId, moduleId) {

    if (requirementId && requirementId !== MANUAL_CASE_REQUIREMENT_ID) return `req:${requirementId}`;

    if (moduleId) return `module:${moduleId}`;

    return "";

  }



  function normalizeCaseFormPayload(form) {

    const normalizedRequirementId =

      form.requirement_id && form.requirement_id !== MANUAL_CASE_REQUIREMENT_ID ? form.requirement_id : "";

    const rows = (form.steps || []).filter((item) => item.step.trim() || item.expected.trim());

    const testPointFallback = form.test_point.trim() || getModuleLabel(form.module_id) || getRequirementLabel(normalizedRequirementId);

    return {

      requirement_id: normalizedRequirementId,

      module_id: normalizedRequirementId ? "" : (form.module_id || ""),

      case_type: form.case_type,

      stage: form.stage,

      title: form.title.trim(),

      test_point: testPointFallback,

      preconditions: form.preconditions_text

        .split(/\r?\n/)

        .map((item) => item.trim())

        .filter(Boolean),

      steps: rows.map((item) => item.step.trim()),

      expected: rows.map((item) => item.expected.trim()),

      priority: form.priority,

      creator: form.creator || "",

    };

  }



  function buildCaseFormFromItem(item = {}) {

    const rows = Math.max(item.steps?.length || 0, item.expected?.length || 0, 3);

    return {

      requirement_id: item.requirement_id && item.requirement_id !== MANUAL_CASE_REQUIREMENT_ID ? item.requirement_id : "",

      module_id: item.module_id || "",

      target_key: getCaseTargetValue(item.requirement_id, item.module_id || ""),

      case_type: item.case_type || "",

      stage: item.stage || "",

      title: item.title || "",

      test_point: item.test_point || "",

      preconditions_text: (item.preconditions || []).join("\n"),

      priority: item.priority || "",

      creator: item.creator || "",

      steps: Array.from({ length: rows }, (_, index) => ({

        id: item.id ? `${item.id}-${index}` : createCaseStep(index + 1).id,

        step: item.steps?.[index] || "",

        expected: item.expected?.[index] || "",

      })),

    };

  }



  function openCaseEditor(mode, item = null) {

    if (mode === "create") {

      const firstTarget = caseTargetOptions[0];

      setCaseForm({

        ...createEmptyCaseForm(firstTarget?.requirementId || "", firstTarget?.moduleId || ""),

        target_key: firstTarget?.key || "",

      });

      setEditingCaseId("");

    } else {

      setCaseForm(buildCaseFormFromItem(item || {}));

      setEditingCaseId(item?.id || "");

    }

    setCaseEditorMode(mode);

  }



  function closeCaseEditor() {

    setCaseEditorMode("list");

    setEditingCaseId("");

    const firstTarget = caseTargetOptions[0];

    setCaseForm({

      ...createEmptyCaseForm(firstTarget?.requirementId || "", firstTarget?.moduleId || ""),

      target_key: firstTarget?.key || "",

    });

  }



  function handleCaseRequirementChange(targetKey) {

    const target = caseTargetOptions.find((item) => item.key === targetKey);

    setCaseForm((prev) => ({

      ...prev,

      target_key: targetKey,

      requirement_id: target?.requirementId || "",

      module_id: target?.moduleId || "",

    }));

  }



  function updateCaseStepRow(rowId, field, value) {

    setCaseForm((prev) => ({

      ...prev,

      steps: prev.steps.map((item) => (item.id === rowId ? { ...item, [field]: value } : item)),

    }));

  }



  function appendCaseStep(afterRowId = "") {

    setCaseForm((prev) => {

      const nextRow = createCaseStep(prev.steps.length + 1);

      if (!afterRowId) {

        return { ...prev, steps: [...prev.steps, nextRow] };

      }

      const index = prev.steps.findIndex((item) => item.id === afterRowId);

      if (index < 0) return { ...prev, steps: [...prev.steps, nextRow] };

      const nextSteps = [...prev.steps];

      nextSteps.splice(index + 1, 0, nextRow);

      return { ...prev, steps: nextSteps };

    });

  }



  function duplicateCaseStep(rowId) {

    setCaseForm((prev) => {

      const index = prev.steps.findIndex((item) => item.id === rowId);

      if (index < 0) return prev;

      const nextSteps = [...prev.steps];

      nextSteps.splice(index + 1, 0, { ...prev.steps[index], id: createCaseStep(index + 1).id });

      return { ...prev, steps: nextSteps };

    });

  }



  function removeCaseStep(rowId) {

    setCaseForm((prev) => {

      if (prev.steps.length <= 1) {

        return { ...prev, steps: [{ ...prev.steps[0], step: "", expected: "" }] };

      }

      return { ...prev, steps: prev.steps.filter((item) => item.id !== rowId) };

    });

  }



  async function submitCaseForm() {

    const payload = normalizeCaseFormPayload(caseForm);

    if (!payload.requirement_id && !payload.module_id) {

      setError("请选择所属模块");

      return;

    }

    if (!payload.title) {

      setError("请输入用例标题");

      return;

    }

    if (payload.steps.length === 0) {

      setError("请至少填写一条用例步骤");

      return;

    }

    await runSafe(async () => {

      if (editingCaseId) {

        await updateTestCase(editingCaseId, payload);

      } else {

        await createTestCase(payload);

      }

      await loadTestCases();

      await loadCaseSidebar();

      closeCaseEditor();

    });

  }



  async function removeCaseItem(caseId) {

    await runSafe(async () => {

      await deleteTestCase(caseId);

      await loadTestCases();

      await loadCaseSidebar();

      if (editingCaseId === caseId) closeCaseEditor();

    });

  }



  function openCaseModuleModal() {

    setEditingCaseModuleId("");

    setCaseModuleForm({ parent_id: "", name: "" });

    setShowCaseModuleModal(true);

  }



  function openCaseModuleEditModal(moduleItem) {

    setEditingCaseModuleId(moduleItem.id);

    setCaseModuleForm({

      parent_id: moduleItem.parent_id || "",

      name: moduleItem.name || "",

    });

    setShowCaseModuleModal(true);

  }



  async function submitCaseModule() {

    if (!caseModuleForm.name.trim()) {

      setError("请输入分组名称");

      return;

    }

    await runSafe(async () => {

      const payload = {

        parent_id: caseModuleForm.parent_id,

        name: caseModuleForm.name.trim(),

      };

      if (editingCaseModuleId) {

        await updateTestCaseModule(editingCaseModuleId, payload);

      } else {

        await createTestCaseModule(payload);

      }

      await loadCaseModules();

      await loadCaseSidebar();

      setShowCaseModuleModal(false);

      setEditingCaseModuleId("");

    });

  }



  async function removeCaseModule(moduleId) {

    await runSafe(async () => {

      await deleteTestCaseModule(moduleId);

      await loadCaseModules();

      await loadCaseSidebar();

    });

  }



  function buildCaseModuleTree() {

    const countMap = {};

    const collectCounts = (nodes = []) => {

      nodes.forEach((node) => {

        countMap[node.id] = node.count || 0;

        collectCounts(node.children || []);

      });

    };

    collectCounts(caseSidebarData.module_tree || []);



    const nodeMap = Object.fromEntries(

      caseModules.map((item) => [

        item.id,

        {

          ...item,

          count: countMap[item.id] || 0,

          children: [],

        },

      ])

    );



    const roots = [];

    Object.values(nodeMap).forEach((node) => {

      if (node.parent_id && nodeMap[node.parent_id]) {

        nodeMap[node.parent_id].children.push(node);

      } else {

        roots.push(node);

      }

    });



    const sortNodes = (nodes) => {

      nodes.sort((a, b) => (

        (a.sort_order || 0) - (b.sort_order || 0)

        || String(a.name || "").localeCompare(String(b.name || ""))

      ));

      nodes.forEach((node) => sortNodes(node.children || []));

    };

    sortNodes(roots);

    return roots;

  }



  function buildRequirementCaseTree() {

    return caseSidebarData.requirement_tree || { id: "requirement-root", name: "需求类", count: 0, children: [] };

  }



  function getTreeCaseCount(node) {

    return node.count || 0;

  }



  function toggleCaseModuleExpanded(moduleId) {

    setExpandedCaseModuleIds((prev) => ({ ...prev, [moduleId]: !prev[moduleId] }));

  }



  async function startReviewForRequirement(requirementId) {

    const state = reviewStates[requirementId];

    if (!state) {

      return;

    }

    await runSafe(async () => {

      const reviewCheckResult = await getReviewChecks();

      const nextReviewOptions = (reviewCheckResult.items || []).map((check) => check.name).filter(Boolean);

      setReviewOptions(nextReviewOptions);

      const selectedChecks = state.selectedChecks.filter((check) => nextReviewOptions.includes(check));

      if (selectedChecks.length === 0) {

        setError("请至少选择一个评审项");

        return;

      }

      const run = await startRequirementReview({ requirement_id: requirementId, checks: selectedChecks });

      setReviewStates((prev) => ({

        ...prev,

        [requirementId]: {

          ...prev[requirementId],

          selectedChecks,

          requirement: {

            ...prev[requirementId].requirement,

            review_status: "评审中",

          },

          currentRunId: run.id,

          runs: [run, ...(prev[requirementId]?.runs || [])],

        },

      }));

      await loadRequirements();

    });

  }



  function toggleReviewCheck(requirementId, checkName) {

    setReviewStates((prev) => {

      const state = prev[requirementId];

      if (!state) return prev;

      let nextChecks;

      if (checkName === ALL_CHECK_KEY) {

        nextChecks = state.selectedChecks.length === reviewOptions.length ? [] : [...reviewOptions];

      } else {

        nextChecks = state.selectedChecks.includes(checkName)

          ? state.selectedChecks.filter((item) => item !== checkName)

          : [...state.selectedChecks, checkName];

      }

      return { ...prev, [requirementId]: { ...state, selectedChecks: nextChecks } };

    });

  }



  function focusAnnotation(requirementId, annotationId, options = {}) {

    if (!annotationId) return;

    const { scrollComment = true, scrollDocument = false } = options;

    setActiveAnnotationIds((prev) => (prev[requirementId] === annotationId ? prev : { ...prev, [requirementId]: annotationId }));



    if (scrollComment) {

      const commentNode = reviewCommentRefs.current[`${requirementId}:${annotationId}`];

      commentNode?.scrollIntoView({ block: "nearest", behavior: "smooth" });

    }



    if (scrollDocument) {

      const container = reviewDocumentRefs.current[requirementId];

      const marker = container?.querySelector(`[data-annotation-id="${annotationId}"]`);

      marker?.scrollIntoView({ block: "center", behavior: "smooth" });

    }

  }



  function handleReviewDocumentScroll(requirementId) {

    const container = reviewDocumentRefs.current[requirementId];

    if (!container) return;

    const markers = [...container.querySelectorAll("[data-annotation-id]")];

    if (markers.length === 0) return;



    const containerTop = container.getBoundingClientRect().top;

    let bestId = markers[0].dataset.annotationId;

    let bestScore = Number.POSITIVE_INFINITY;



    markers.forEach((node) => {

      const nodeTop = node.getBoundingClientRect().top - containerTop;

      const score = nodeTop >= 0 ? nodeTop : Math.abs(nodeTop) + 200;

      if (score < bestScore) {

        bestScore = score;

        bestId = node.dataset.annotationId;

      }

    });



    focusAnnotation(requirementId, bestId, { scrollComment: true, scrollDocument: false });

  }



  function handleReviewDocumentClick(event, requirementId) {

    const target = event.target.closest("[data-annotation-id]");

    if (!target) return;

    focusAnnotation(requirementId, target.dataset.annotationId, { scrollComment: true, scrollDocument: false });

  }



  function exportCurrentTable() {

    const headers = ["项目", "标题", "评审状态", "创建人", "创建时间"];

    const rows = requirements.map((item) => [

      item.project,

      item.title,

      getReviewStatusLabel(item.review_status),

      item.creator,

      item.created_date,

    ]);

    const csv = [headers, ...rows]

      .map((line) => line.map((cell) => `"${String(cell || "").replaceAll('"', '""')}"`).join(","))

      .join("\n");

    const blob = new Blob([`﻿${csv}`], { type: "text/csv;charset=utf-8;" });

    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");

    a.href = url;

    a.download = "requirements.csv";

    a.click();

    URL.revokeObjectURL(url);

  }

  function getCaseExportScopeName() {

    if (selectedCaseScope.kind === "module") return getModuleLabel(selectedCaseScope.value) || "未命名模块";

    if (selectedCaseScope.kind === "requirement") return getRequirementLabel(selectedCaseScope.value) || "未命名需求";

    if (selectedCaseScope.kind === "project") return projectMap[selectedCaseScope.value]?.name || "未命名项目";

    if (selectedCaseScope.kind === "requirement_root") return "需求树";

    return "全部用例";

  }



  function formatExportList(value) {

    if (Array.isArray(value)) {

      const items = value

        .map((item, index) => `${index + 1}. ${String(item || "").trim()}`)

        .filter((entry) => !entry.endsWith(". "));

      return items.length ? items.join("\n") : "-";

    }

    const textValue = String(value || "").trim();

    return textValue || "-";

  }



  function buildCaseExportRow(item, index) {

    const requirement = requirementMap[item.requirement_id] || null;

    const priorityLabel = casePriorityLabelMap[item.priority] || item.priority || "-";

    const caseTypeLabel = caseTypeOptions.find((option) => option.key === item.case_type)?.value || item.case_type_label || item.case_type || "-";

    const systemName = requirement?.project || projectMap[requirement?.project_id || ""]?.name || "-";

    return {

      serial: index + 1,

      system_name: systemName,

      module_name: item.module_name || getModuleLabel(item.module_id) || getRequirementLabel(item.requirement_id) || "-",

      requirement_no: item.requirement_id && item.requirement_id !== MANUAL_CASE_REQUIREMENT_ID ? item.requirement_id : "-",

      requirement_name: getRequirementLabel(item.requirement_id) || "-",

      title: item.title || "-",

      preconditions_text: formatExportList(item.preconditions),

      steps_text: formatExportList(item.steps),

      expected_text: formatExportList(item.expected),

      priority_label: priorityLabel,

      case_type: caseTypeLabel,

      stage: item.stage || "-",

      test_data: "",

      actual_result: "",

      test_status: item.review_status || "",

      test_point: item.test_point || "-",

      creator: item.creator || "-",

      created_at: (item.created_at || "").replace("T", " ").replace("Z", "") || "-",

    };

  }



  function renderExportCell(value) {

    return escapeHtml(String(value ?? "-")).replaceAll("\n", "<br />");

  }



  function getSelectedCaseExportColumns() {

    return caseExportFields

      .map((key) => CASE_EXPORT_FIELD_COLUMNS.find((item) => item.key === key) || (CASE_EXPORT_FIELD_LABEL_MAP[key] ? { key, label: CASE_EXPORT_FIELD_LABEL_MAP[key] } : null))

      .filter(Boolean);

  }



  function moveCaseExportField(key, direction) {

    setCaseExportFields((prev) => {

      const index = prev.indexOf(key);

      const nextIndex = direction === "up" ? index - 1 : index + 1;

      if (index < 0 || nextIndex < 0 || nextIndex >= prev.length) return prev;

      const next = [...prev];

      const [field] = next.splice(index, 1);

      next.splice(nextIndex, 0, field);

      return next;

    });

  }



  function reorderCaseExportField(sourceKey, targetKey) {

    if (!sourceKey || !targetKey || sourceKey === targetKey) return;

    setCaseExportFields((prev) => {

      const sourceIndex = prev.indexOf(sourceKey);

      const targetIndex = prev.indexOf(targetKey);

      if (sourceIndex < 0 || targetIndex < 0) return prev;

      const next = [...prev];

      const [field] = next.splice(sourceIndex, 1);

      next.splice(targetIndex, 0, field);

      return next;

    });

  }



  function toggleCaseExportField(key) {

    setCaseExportFields((prev) => {

      if (prev.includes(key)) {

        if (prev.length === 1) return prev;

        return prev.filter((item) => item !== key);

      }

      return [...prev, key];

    });

  }



  function resetCaseExportConfig(format = caseExportFormat) {

    setCaseExportFields(getDefaultCaseExportFields(format));

    setCaseExportStyle(cloneCaseExportStyle(format));

    setDraggingCaseExportField("");

    setShowCaseExportFieldMenu(false);

  }



  function buildExcelExportDocument(rows, scopeName, generatedAt, style, columns) {

    const headerHtml = columns.map((item) => `<th>${escapeHtml(item.label)}</th>`).join("");

    const bodyHtml = rows.map((row) => `<tr>${columns.map((col) => `<td>${renderExportCell(row[col.key])}</td>`).join("")}</tr>`).join("");

    return `<!DOCTYPE html>

<html>

<head>

<meta charset="utf-8" />

<style>

body { font-family: "Microsoft YaHei", sans-serif; color: ${style.bodyText}; margin: 0; }

.export-shell { padding: 16px; }

.export-title { font-size: ${style.titleSize}px; font-weight: 700; margin: 0 0 12px; color: ${style.titleColor}; }

.export-meta { margin: 0 0 16px; color: ${style.metaColor}; font-size: ${style.bodySize}px; }

table { width: 100%; border-collapse: collapse; table-layout: fixed; }

th, td { border: 1px solid ${style.borderColor}; padding: 10px 8px; vertical-align: top; word-break: break-word; }

th { background: ${style.headerBg}; color: ${style.headerText}; font-weight: 700; text-align: left; font-size: ${style.headerSize}px; }

td { background: #ffffff; color: ${style.bodyText}; white-space: pre-wrap; line-height: 1.7; font-size: ${style.bodySize}px; }

</style>

</head>

<body>

<div class="export-shell">

  <div class="export-title">${escapeHtml(style.titleText || "用例导出")}</div>

  <div class="export-meta">导出范围：${escapeHtml(scopeName)} | 导出时间：${escapeHtml(generatedAt)} | 共 ${rows.length} 条</div>

  <table><thead><tr>${headerHtml}</tr></thead><tbody>${bodyHtml}</tbody></table>

</div>

</body>

</html>`;

  }



  function renderWordFieldCells(label, value) {

    return `<tr><td class="case-label" style="width: 14%;">${escapeHtml(label)}</td><td class="case-value case-rich" colspan="3">${renderExportCell(value)}</td></tr>`;

  }



  function buildWordExportDocument(rows, style) {

    const cardsHtml = rows.map((row) => `

      <section class="case-card">

        <div class="case-title"><span class="case-title-index">${escapeHtml(style.titleText || "\u6d4b\u8bd5\u7528\u4f8b")} ${row.serial}:</span><span class="case-title-link">${escapeHtml(row.title || "-")}</span></div>

        <table class="case-table">

          <tr>

            <td class="case-label" style="width: 14%;">\u7528\u4f8b\u540d\u79f0</td>

            <td class="case-value" colspan="3">${renderExportCell(row.title)}</td>

          </tr>

          <tr>

            <td class="case-label">\u6d4b\u8bd5\u7c7b\u578b</td>

            <td class="case-value">${renderExportCell(row.case_type)}</td>

            <td class="case-label">\u4f18\u5148\u7ea7</td>

            <td class="case-value">${renderExportCell(row.priority_label)}</td>

          </tr>

          <tr>

            <td class="case-label">\u524d\u7f6e\u6761\u4ef6</td>

            <td class="case-value">${renderExportCell(row.preconditions_text)}</td>

            <td class="case-label">\u6d4b\u8bd5\u6570\u636e</td>

            <td class="case-value">${renderExportCell(row.test_data || "")}</td>

          </tr>

          <tr>

            <td class="case-label">\u6d4b\u8bd5\u70b9</td>

            <td class="case-label">\u6d4b\u8bd5\u6b65\u9aa4</td>

            <td class="case-label">\u9884\u671f\u7ed3\u679c</td>

            <td class="case-label">\u5b9e\u9645\u7ed3\u679c</td>

          </tr>

          <tr>

            <td class="case-value case-rich">${renderExportCell(row.test_point)}</td>

            <td class="case-value case-rich">${renderExportCell(row.steps_text)}</td>

            <td class="case-value case-rich">${renderExportCell(row.expected_text)}</td>

            <td class="case-value case-rich">${renderExportCell(row.actual_result || "")}</td>

          </tr>

          <tr>

            <td class="case-label">\u6267\u884c\u7ed3\u679c</td>

            <td class="case-value">${renderExportCell(row.test_status || "")}</td>

            <td class="case-label"></td>

            <td class="case-value"></td>

          </tr>

        </table>

      </section>

      <div class="case-gap"></div>

    `).join("");

    return `<!DOCTYPE html>

<html>

<head>

<meta charset="utf-8" />

<style>

body { font-family: "Microsoft YaHei", sans-serif; color: ${style.bodyText}; margin: 0; }

.export-shell { padding: 12px; }

.case-card { margin: 0; page-break-inside: avoid; }

.case-gap { height: 28px; }

.case-title { font-size: ${style.titleSize}px; font-weight: 700; margin: 0 0 16px; }

.case-title-index { color: #111827; margin-right: 8px; }

.case-title-link { color: ${style.titleColor}; text-decoration: underline; }

.case-table { width: 100%; border-collapse: collapse; table-layout: fixed; }

.case-table td { border: 1px solid ${style.borderColor}; padding: 10px 14px; font-size: ${style.bodySize}px; vertical-align: top; word-break: break-word; }

.case-label { background: ${style.headerBg}; color: ${style.headerText}; font-weight: 700; text-align: left; font-size: ${style.headerSize}px; }

.case-value { background: #ffffff; color: ${style.bodyText}; }

.case-rich { white-space: pre-wrap; line-height: 1.8; }

</style>

</head>

<body>

<div class="export-shell">${cardsHtml}</div>

</body>

</html>`;

  }



  function getCaseExportPreviewHtml() {

    const columns = getSelectedCaseExportColumns();

    const sampleRows = [CASE_EXPORT_SAMPLE_ROW];

    if (caseExportFormat === "excel") {

      return buildExcelExportDocument(sampleRows, "预览范围", "2026-03-20 10:00:00", caseExportStyle, columns);

    }

    return buildWordExportDocument(sampleRows, caseExportStyle);

  }



  async function loadAllCasesForExport() {

    const pageSize = 1000;

    let page = 1;

    let items = [];

    let total = 0;

    while (true) {

      const result = await getTestCases({ ...currentCaseQuery, page, page_size: pageSize });

      const pageItems = result.items || [];

      items = items.concat(pageItems);

      total = result.total || items.length;

      if (items.length >= total || pageItems.length === 0) break;

      page += 1;

    }

    return items;

  }



  async function submitCaseExport() {

    setExportingCases(true);

    setError("");

    try {

      const items = await loadAllCasesForExport();

      const rows = items.map(buildCaseExportRow);

      const generatedAt = new Date().toLocaleString("zh-CN", { hour12: false });

      const scopeName = getCaseExportScopeName();

      const columns = getSelectedCaseExportColumns();

      const output = caseExportFormat === "excel"

        ? buildExcelExportDocument(rows, scopeName, generatedAt, caseExportStyle, columns)

        : buildWordExportDocument(rows, caseExportStyle);

      const blob = new Blob([`﻿${output}`], {

        type: caseExportFormat === "excel" ? "application/vnd.ms-excel;charset=utf-8;" : "application/msword;charset=utf-8;",

      });

      const url = URL.createObjectURL(blob);

      const a = document.createElement("a");

      a.href = url;

      a.download = `cases-export-${Date.now()}.${caseExportFormat === "excel" ? "xls" : "doc"}`;

      a.click();

      URL.revokeObjectURL(url);

      setShowCaseExportModal(false);

    } catch (e) {

      setError(e.message || "导出失败");

    } finally {

      setExportingCases(false);

    }

  }



  function renderProjects() {

    const pageCount = Math.max(1, Math.ceil(projectTotal / projectFilters.page_size));

    return (

      <>

        <section className="panel project-search-row">

          <div className="project-search-controls">

            <div className="project-search-box">

              <input value={projectFilters.keyword} placeholder="搜索项目名称/描述" onChange={(e) => setProjectFilters((prev) => ({ ...prev, keyword: e.target.value }))} />

            </div>

            <button className="btn action project-query-btn" onClick={() => runSafe(() => loadProjects({ page: 1 }))}>查询</button>

          </div>

          <button className="btn action" onClick={openProjectCreate}>{"新增项目"}</button>

        </section>

        <section className="panel table-wrap">

          <table className="data-table">

            <thead><tr><th>{"序号"}</th><th>{"项目名称"}</th><th>{"项目描述"}</th><th>{"创建人"}</th><th>{"创建时间"}</th><th>{"操作"}</th></tr></thead>

            <tbody>

              {projects.length === 0 && <tr><td colSpan="6" className="empty">{"暂无数据"}</td></tr>}

              {projects.map((item, idx) => <tr key={item.id}><td>{(projectFilters.page - 1) * projectFilters.page_size + idx + 1}</td><td>{item.name}</td><td>{item.description || "无描述"}</td><td>{item.creator || ""}</td><td>{item.created_at?.replace("T", " ").slice(0, 19)}</td><td><button className="mini-btn" onClick={() => openProjectEdit(item)}>{"编辑"}</button><button className="mini-btn danger" onClick={() => removeProject(item.id)}>{"删除"}</button></td></tr>)}

            </tbody>

          </table>

          <div className="pagination right"><div>{"共 "}{projectTotal}{" 条"}</div><div className="pagination-actions"><button className="btn ghost" disabled={projectFilters.page <= 1} onClick={() => runSafe(() => loadProjects({ page: projectFilters.page - 1 }))}>{"上一页"}</button><span>{projectFilters.page}</span><button className="btn ghost" disabled={projectFilters.page >= pageCount} onClick={() => runSafe(() => loadProjects({ page: projectFilters.page + 1 }))}>{"下一页"}</button><select value={projectFilters.page_size} onChange={(e) => runSafe(() => loadProjects({ page: 1, page_size: Number(e.target.value) }))}><option value={10}>{"10 条/页"}</option><option value={20}>{"20 条/页"}</option><option value={50}>{"50 条/页"}</option></select></div></div>

        </section>

      </>

    );

  }



  function renderDatePicker(field) {

    const panelMonth = datePanelMonths[field] || getPanelMonthState("");

    const draft = dateDrafts[field] || { date: "", time: "" };

    const [selectedHour = "00", selectedMinute = "00"] = (draft.time || "00:00").split(":");

    const dayCells = getCalendarDays(panelMonth.year, panelMonth.month);



    return (

      <div className="date-picker-popover">

        <div className="date-picker-header">

          <div className="date-picker-nav">

            <button type="button" className="date-nav-btn" onClick={() => shiftPanelMonth(field, -1)}>{"<"}</button>

            <button type="button" className="date-nav-btn" onClick={() => shiftPanelMonth(field, 1)}>{">"}</button>

          </div>

          <div className="date-picker-title">{formatPanelMonth(panelMonth.year, panelMonth.month)}</div>

        </div>

        <div className="date-picker-main">

          <div className="date-calendar">

            <div className="date-weekdays">

              {WEEKDAY_LABELS.map((label) => <span key={label}>{label}</span>)}

            </div>

            <div className="date-days-grid">

              {dayCells.map((cell) => {

                const cellValue = formatDateValue(cell.date);

                const isSelected = isSameDate(cellValue, draft.date);

                return (

                  <button

                    type="button"

                    key={`${field}-${cellValue}`}

                    className={`date-day-cell${cell.currentMonth ? "" : " muted"}${isSelected ? " active" : ""}`}

                    onClick={() => {

                      selectDraftDate(field, cellValue);

                      setDatePanelMonths((prev) => ({

                        ...prev,

                        [field]: { year: cell.date.getFullYear(), month: cell.date.getMonth() },

                      }));

                    }}

                  >

                    {cell.day}

                  </button>

                );

              })}

            </div>

          </div>

          <div className="date-time-columns">

            <div className="time-column">

              {HOUR_OPTIONS.map((hour) => <button type="button" key={`${field}-h-${hour}`} className={`time-option${selectedHour === hour ? " active" : ""}`} onClick={() => selectDraftHour(field, hour)}>{hour}</button>)}

            </div>

            <div className="time-column">

              {MINUTE_OPTIONS.map((minute) => <button type="button" key={`${field}-m-${minute}`} className={`time-option${selectedMinute === minute ? " active" : ""}`} onClick={() => selectDraftMinute(field, minute)}>{minute}</button>)}

            </div>

          </div>

        </div>

        <div className="date-picker-popover-actions">

          <button type="button" className="btn action small" onClick={() => applyDateDraft(field)}>{"确定"}</button>

        </div>

      </div>

    );

  }



  function renderRequirements() {

    const pageCount = Math.max(1, Math.ceil(reqTotal / reqFilters.page_size));

    const allSelected = requirements.length > 0 && selectedIds.length === requirements.length;

    return (

      <>

        <section className="panel requirement-search-row">

          <div className="date-filter"><label>{"创建时间"}</label><div className="date-range-field"><div className="date-input-wrap" ref={(node) => { datePanelRefs.current.start_date = node; }}><input className="date-display-input" type="text" value={dateInputTexts.start_date} onChange={(e) => changeDateInputText("start_date", e.target.value)} onBlur={() => commitDateInput("start_date")} onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); commitDateInput("start_date"); } }} />{reqFilters.start_date && <button type="button" className="date-clear-btn" onClick={(e) => { e.stopPropagation(); clearDateFilter("start_date"); }}>&times;</button>}<button type="button" className="date-picker-btn" aria-label={"选择开始时间"} onClick={() => openDatePicker("start_date")} />{activeDatePanel === "start_date" && renderDatePicker("start_date")}</div><span className="dash">~</span><div className="date-input-wrap" ref={(node) => { datePanelRefs.current.end_date = node; }}><input className="date-display-input" type="text" value={dateInputTexts.end_date} onChange={(e) => changeDateInputText("end_date", e.target.value)} onBlur={() => commitDateInput("end_date")} onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); commitDateInput("end_date"); } }} />{reqFilters.end_date && <button type="button" className="date-clear-btn" onClick={(e) => { e.stopPropagation(); clearDateFilter("end_date"); }}>&times;</button>}<button type="button" className="date-picker-btn" aria-label={"选择结束时间"} onClick={() => openDatePicker("end_date")} />{activeDatePanel === "end_date" && renderDatePicker("end_date")}</div></div></div>

          <div className="compact-field project-field"><label>{"项目"}</label><select value={reqFilters.project_id} onChange={(e) => setReqFilters((prev) => ({ ...prev, project_id: e.target.value }))}><option value="">{"全部项目"}</option>{projects.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></div>

          <div className="compact-field status-field"><label>{"评审状态"}</label><select value={reqFilters.review_status} onChange={(e) => setReqFilters((prev) => ({ ...prev, review_status: e.target.value }))}><option value="">{"全部"}</option><option value={"待评审"}>{"未开始"}</option><option value={"评审中"}>{"进行中"}</option><option value={"评审完成"}>{"已完成"}</option></select></div>

          <div className="compact-field creator-field"><label>{"创建人"}</label><input value={reqFilters.creator} placeholder={"全部"} onChange={(e) => setReqFilters((prev) => ({ ...prev, creator: e.target.value }))} /></div>

          <div className="compact-field keyword-box"><input value={reqFilters.keyword} placeholder={"输入标题"} onChange={(e) => setReqFilters((prev) => ({ ...prev, keyword: e.target.value }))} /></div>

          <button className="btn action" onClick={() => runSafe(() => loadRequirements({ page: 1 }))}>{"查询"}</button>

          <button className="btn ghost" onClick={resetFilters}>{"重置"}</button>

        </section>

        <section className="panel top-actions-row"><div className="left-actions"><button className="btn action" onClick={openImportModal}>{"上传需求文档"}</button><button className="btn danger" onClick={removeBatch} disabled={selectedIds.length === 0}>{"批量删除"}</button></div><button className="btn export" onClick={exportCurrentTable}>{"导出"}</button></section>

        <section className="panel table-wrap">

          <table className="data-table">

            <thead><tr><th><input type="checkbox" checked={allSelected} onChange={(e) => toggleSelectAll(e.target.checked)} /></th><th>{"序号"}</th><th>{"项目"}</th><th>{"标题"}</th><th>{"导入方式"}</th><th>{"评审状态"}</th><th>{"创建人"}</th><th>{"创建时间"}</th><th>{"操作"}</th></tr></thead>

            <tbody>

              {requirements.length === 0 && <tr><td colSpan="9" className="empty">{"暂无数据"}</td></tr>}

              {requirements.map((item, idx) => <tr key={item.id}><td><input type="checkbox" checked={selectedIds.includes(item.id)} onChange={() => toggleSelect(item.id)} /></td><td>{(reqFilters.page - 1) * reqFilters.page_size + idx + 1}</td><td>{item.project}</td><td>{item.title}</td><td>{item.import_method === "jira" ? "Jira 链接" : item.import_method === "file" ? "上传文件" : "手工录入"}</td><td><span className={item.review_status === "评审完成" ? "tag success" : item.review_status === "评审中" ? "tag info" : "tag wait"}>{getReviewStatusLabel(item.review_status)}</span></td><td>{item.creator}</td><td>{item.created_date}</td><td><button className="link" onClick={() => openReviewPage(item)}>{"详情"}</button><button className="link" onClick={() => openReviewPage(item)}>{item.latest_review_run_id || item.review_status === "评审完成" || item.review_status === "评审中" ? "重新评审" : "开始评审"}</button><button className="link" onClick={() => openCaseWorkflowPage(item)}>{"关联用例"}</button><button className="link link-danger" onClick={() => removeRequirement(item.id)}>{"删除"}</button></td></tr>)}

            </tbody>

          </table>

          <div className="pagination"><div>{"共 "}{reqTotal}{" 条"}</div><div className="pagination-actions"><button className="btn ghost" disabled={reqFilters.page <= 1} onClick={() => runSafe(() => loadRequirements({ page: reqFilters.page - 1 }))}>{"上一页"}</button><span>{reqFilters.page} / {pageCount}</span><button className="btn ghost" disabled={reqFilters.page >= pageCount} onClick={() => runSafe(() => loadRequirements({ page: reqFilters.page + 1 }))}>{"下一页"}</button><select value={reqFilters.page_size} onChange={(e) => runSafe(() => loadRequirements({ page: 1, page_size: Number(e.target.value) }))}><option value={10}>{"10 条/页"}</option><option value={20}>{"20 条/页"}</option><option value={50}>{"50 条/页"}</option></select></div></div>

        </section>

      </>

    );

  }



  function renderReviewPage(requirementId) {

    const state = reviewStates[requirementId];

    if (!state?.requirement) {

      return <section className="panel placeholder"><p>{"正在加载评审数据..."}</p></section>;

    }



    const currentRun = state.runs.find((item) => item.id === state.currentRunId) || state.runs[0] || null;

    const activeChecks = (currentRun?.checks?.length ? currentRun.checks : state.selectedChecks).filter(Boolean);

    const annotations = currentRun?.results.flatMap((item) => item.annotations || []) || [];

    const summaryRemark = buildSummaryRemark(currentRun);

    const commentMode = reviewCommentModes[requirementId] || "summary";

    const annotatedHtml = buildAnnotatedHtml(state.requirement, annotations);

    const allSelected = reviewOptions.length > 0 && state.selectedChecks.length === reviewOptions.length;

    const reviewFailed = currentRun?.status === "failed";

    const reviewError = currentRun?.error || "";



    return (

      <section className="review-page">

        <div className="panel review-header-card">

          <div className="review-header-left">

            <button className="back-link" onClick={() => setActiveTabKey("requirements")}>{"← 返回列表"}</button>

          </div>

          <div className="review-header-main">

            <div className="review-title-row">

              <h2>{state.requirement.title}</h2>

              <span className={state.requirement.review_status === "评审完成" ? "tag success" : state.requirement.review_status === "评审中" ? "tag info" : "tag wait"}>{state.requirement.review_status || "待评审"}</span>

            </div>

          </div>

          <div className="review-header-right">

            <div className="review-toolbar-row">

              <label className="review-select-label">{"评审项"}</label>

              <div

                className={reviewSelectOpenId === requirementId ? "review-multiselect open" : "review-multiselect"}

                ref={(node) => {

                  reviewSelectRefs.current[requirementId] = node;

                }}

              >

                <button

                  type="button"

                  className="review-multiselect-trigger"

                  onClick={() => setReviewSelectOpenId((prev) => (prev === requirementId ? "" : requirementId))}

                >

                  <div className="review-multiselect-values">

                    {state.selectedChecks.length === 0 && <span className="review-multiselect-placeholder">{"请选择评审项"}</span>}

                    {state.selectedChecks.map((item) => <span key={item} className="review-selected-chip">{item}<span className="review-selected-chip-close" onClick={(event) => {

                      event.stopPropagation();

                      toggleReviewCheck(requirementId, item);

                    }}>{"×"}</span></span>)}

                  </div>

                  <span className="review-multiselect-arrow">{reviewSelectOpenId === requirementId ? "▲" : "▼"}</span>

                </button>

                {reviewSelectOpenId === requirementId && <div className="review-multiselect-menu"><button type="button" className={allSelected ? "review-multiselect-option active" : "review-multiselect-option"} onClick={() => {

                  toggleReviewCheck(requirementId, ALL_CHECK_KEY);

                  setReviewSelectOpenId("");

                }}><span>{"全部"}</span><span>{allSelected ? "✓" : ""}</span></button>{reviewOptions.map((item) => <button key={item} type="button" className={state.selectedChecks.includes(item) ? "review-multiselect-option active" : "review-multiselect-option"} onClick={() => {

                  toggleReviewCheck(requirementId, item);

                }}><span>{item}</span><span>{state.selectedChecks.includes(item) ? "✓" : ""}</span></button>)}</div>}

              </div>

              <button className="btn action review-start-btn" onClick={() => {

                setReviewSelectOpenId("");

                startReviewForRequirement(requirementId);

              }}>{"开始评审"}</button>

            </div>

          </div>

        </div>



        <div className="panel review-flow-card">

          <div className="review-flow-title">{"评审工作流程"}</div>

          <div className="review-flow-row dynamic">

            {activeChecks.map((item, index) => {

              const completed = currentRun?.results.some((result) => result.name === item);

              const current = currentRun?.status === "running" && !completed;

              return <div key={item} className="flow-step"><div className={completed ? "flow-icon done" : current ? "flow-icon current" : "flow-icon"}>{completed ? "✓" : index + 1}</div><div className="flow-label">{item}</div></div>;

            })}

            <div className="flow-step"><div className={currentRun?.status === "completed" ? "flow-icon done" : "flow-icon"}>{currentRun?.status === "completed" ? "✓" : activeChecks.length + 1}</div><div className="flow-label">{"评审完成"}</div></div>

          </div>

        </div>

        {reviewFailed && (

          <div className="error-banner">{`AI 评审失败：${reviewError || "请稍后重试"}`}</div>

        )}

        <div className="panel review-unified-panel">

          <div className="review-unified-head">

            <div className="review-section-title">{"需求正文"}</div>

            <div className="review-section-title">{"评审备注"}</div>

          </div>

          <div className="review-content-layout same-module">

            <div

              className="review-document-surface"

              ref={(node) => {

                reviewDocumentRefs.current[requirementId] = node;

              }}

              onScroll={() => handleReviewDocumentScroll(requirementId)}

              onClick={(event) => handleReviewDocumentClick(event, requirementId)}

              dangerouslySetInnerHTML={{ __html: annotatedHtml }}

            />

            <div className="review-comment-list integrated">

              <div className="review-comment-tabs">

                <button

                  type="button"

                  className={commentMode === "summary" ? "review-comment-tab active" : "review-comment-tab"}

                  onClick={() => setReviewCommentModes((prev) => ({ ...prev, [requirementId]: "summary" }))}

                >

                  {"总结"}

                </button>

                <button

                  type="button"

                  className={commentMode === "detail" ? "review-comment-tab active" : "review-comment-tab"}

                  onClick={() => setReviewCommentModes((prev) => ({ ...prev, [requirementId]: "detail" }))}

                >

                  {"详情"}

                </button>

              </div>



              <div className="review-comment-body">

                {commentMode === "summary" && (

                  <div className="review-summary-scroll">

                    {!summaryRemark && <div className="review-running-tip">{"开始评审后，这里会显示总体评价、分数、一句话总结、优势点和改进点。"}</div>}

                    {reviewFailed && <div className="review-running-tip">{"AI 评审未成功完成，请根据错误信息调整后重试。"}</div>}

                    {summaryRemark && (

                      <section className="review-summary-card">

                        <div className="review-summary-hero">

                          <div className="review-summary-score">

                            <strong>{summaryRemark.score}</strong>

                            <span>{"总分"}</span>

                          </div>

                          <div className="review-summary-overview">

                            <h3>{summaryRemark.headline}</h3>

                            <div className="review-summary-level">{summaryRemark.level}</div>

                          </div>

                        </div>

                        <div className="review-summary-section review-summary-oneline">

                          <h4>{summaryRemark.oneLineTitle}</h4>

                          <p>{summaryRemark.oneLineSummary}</p>

                        </div>

                        <div className="review-summary-section review-summary-strengths">

                          <h4>{summaryRemark.strengthsTitle}</h4>

                          {summaryRemark.strengths.map((item, index) => (

                            <p key={`strength-${index}`}>{item}</p>

                          ))}

                        </div>

                        <div className="review-summary-section review-summary-improvements">

                          <h4>{summaryRemark.improvementsTitle}</h4>

                          {summaryRemark.improvements.map((item, index) => (

                            <p key={`improvement-${index}`}>{item}</p>

                          ))}

                        </div>

                      </section>

                    )}

                  </div>

                )}



                {commentMode === "detail" && (

                  <div className="review-detail-scroll">

                    {annotations.length === 0 && <div className="review-running-tip">{"开始评审后，这里会按命中语句输出针对性的建议。"}</div>}

                    {reviewFailed && <div className="review-running-tip">{`评审生成失败：${reviewError || "请稍后重试"}`}</div>}

                    {annotations.map((annotation, index) => {

                      const isActive = activeAnnotationIds[requirementId] === annotation.id;

                      const analysisClass = getAnalysisClass(annotation.comment_title);

                      return <article key={annotation.id} className={isActive ? `comment-card active ${analysisClass}` : `comment-card ${analysisClass}`} ref={(node) => {

                        reviewCommentRefs.current[`${requirementId}:${annotation.id}`] = node;

                      }} onClick={() => focusAnnotation(requirementId, annotation.id, { scrollComment: false, scrollDocument: true })}><div className={`comment-badge ${analysisClass}`}>{index + 1}</div><div className="comment-body"><div className={`comment-title ${analysisClass}`}>{annotation.comment_title}</div><div className={`comment-quote ${analysisClass}`}>{annotation.quote}</div><div className="comment-text">{annotation.comment}</div><div className="comment-suggestion">{"建议："}{annotation.suggestion}</div></div></article>;

                    })}

                    {currentRun?.status === "running" && <div className="review-running-tip">{"AI 正在持续输出评审结果，当前页面会自动联动定位到相关备注。"}</div>}

                  </div>

                )}

              </div>

            </div>

          </div>

        </div>

      </section>

    );

  }



  function renderCasesSidebar() {

    const moduleTree = buildCaseModuleTree();

    const requirementTree = buildRequirementCaseTree();

    const allCount = caseSidebarData.all_count || 0;

    const keyword = caseModuleKeyword.trim().toLowerCase();



    function matchesModuleKeyword(node) {

      if (!keyword) return true;

      if (node.name.toLowerCase().includes(keyword)) return true;

      return node.children.some((child) => matchesModuleKeyword(child));

    }



    function renderModuleNode(node, depth = 0, kind = "module") {

      const count = kind === "module" ? getTreeCaseCount(node) : node.count || 0;

      const expanded = expandedCaseModuleIds[node.id] !== false;

      const hasChildren = node.children.length > 0;

      const active =

        (kind === "module" && selectedCaseScope.kind === "module" && selectedCaseScope.value === node.id)

        || (kind === "project" && selectedCaseScope.kind === "project" && selectedCaseScope.value === (node.project_id || node.projectId))

        || (kind === "requirement" && selectedCaseScope.kind === "requirement" && selectedCaseScope.value === (node.requirement_id || node.requirementId))

        || (kind === "requirement_root" && selectedCaseScope.kind === "requirement_root");



      function handleSelect() {

        if (kind === "module") setSelectedCaseScope({ kind: "module", value: node.id });

        if (kind === "project") setSelectedCaseScope({ kind: "project", value: node.project_id || node.projectId || "" });

        if (kind === "requirement") setSelectedCaseScope({ kind: "requirement", value: node.requirement_id || node.requirementId || "" });

        if (kind === "requirement_root") setSelectedCaseScope({ kind: "requirement_root", value: "" });

      }



      return (

        <div key={node.id} className="cases-tree-node">

          <div className={active ? "cases-tree-row active" : "cases-tree-row"} style={{ paddingLeft: `${8 + depth * 18}px` }}>

            <button

              type="button"

              className={hasChildren ? "cases-tree-toggle" : "cases-tree-toggle placeholder"}

              onClick={() => hasChildren && toggleCaseModuleExpanded(node.id)}

            >

              {hasChildren ? (expanded ? "▼" : "▶") : ""}

            </button>

            <button

              type="button"

              className="cases-tree-label"

              onClick={handleSelect}

            >

              <span>{`${node.name}(${count})`}</span>

            </button>

            {kind === "module" && (

              <div className="cases-tree-actions">

                <button type="button" className="cases-tree-icon-btn" onClick={() => openCaseModuleEditModal(node)} title="编辑">

                  ✎

                </button>

                <button type="button" className="cases-tree-icon-btn danger" onClick={() => removeCaseModule(node.id)} title="删除">

                  ×

                </button>

              </div>

            )}

          </div>

          {hasChildren && expanded && (

            <div className="cases-tree-children">

              {node.children.map((child) =>

                renderModuleNode(

                  child,

                  depth + 1,

                  kind === "requirement_root" ? "project" : kind === "project" ? "requirement" : "module"

                )

              )}

            </div>

          )}

        </div>

      );

    }



    return (

      <aside className="panel cases-module-panel">

        <div className="cases-module-head">

          <div>

            <div className="cases-panel-title">模块管理</div>

            <div className="cases-panel-subtitle">按所属模块快速筛选用例</div>

          </div>

          <button

            type="button"

            className="cases-sidebar-toggle"

            onClick={() => setCaseSidebarCollapsed((prev) => !prev)}

            aria-label="收起模块管理"

            title="收起模块管理"

          >

            ◀

          </button>

        </div>

        <div className="cases-module-search">

          <input

            value={caseModuleKeyword}

            onChange={(event) => setCaseModuleKeyword(event.target.value)}

            placeholder={CASE_SIDEBAR_TEXT.searchPlaceholder}

          />

        </div>

        <button type="button" className="btn action small cases-module-add-btn" onClick={openCaseModuleModal}>

          {CASE_SIDEBAR_TEXT.add}

        </button>

        <div className="cases-module-tree">

          <div className={selectedCaseScope.kind === "all" ? "cases-tree-row active active-all" : "cases-tree-row active-all"}>

            <button type="button" className="cases-tree-toggle placeholder" />

            <button type="button" className="cases-tree-label" onClick={() => setSelectedCaseScope({ kind: "all", value: "" })}>

              <span>{`${CASE_SIDEBAR_TEXT.allPrefix}?${allCount}?`}</span>

            </button>

          </div>

          {requirementTree.count > 0 && matchesModuleKeyword(requirementTree) && renderModuleNode(requirementTree, 0, "requirement_root")}

          {moduleTree.length === 0 && requirementTree.count === 0 && <div className="empty-tip">{CASE_SIDEBAR_TEXT.empty}</div>}

          {moduleTree.filter((node) => matchesModuleKeyword(node)).map((node) => renderModuleNode(node))}

        </div>

      </aside>

    );

  }



  function renderCasesLayout(rightContent, options = {}) {

    const { editorMode = false } = options;

    const layoutClass = [

      "cases-layout",

      caseSidebarCollapsed ? "sidebar-collapsed" : "",

      editorMode ? "editor-mode" : "list-mode",

    ].filter(Boolean).join(" ");

    const mainClass = [

      "cases-main",

      editorMode ? "cases-main-editor" : "cases-main-list",

    ].join(" ");



    return (

      <section className="cases-page">

        <div className={layoutClass}>

          {!caseSidebarCollapsed && renderCasesSidebar()}

          <div className={mainClass}>

            {caseSidebarCollapsed && !editorMode && (

              <button

                type="button"

                className="cases-sidebar-expand"

                onClick={() => setCaseSidebarCollapsed(false)}

                aria-label="展开模块管理"

                title="展开模块管理"

              >

                ▶ 模块管理

              </button>

            )}

            {rightContent}

          </div>

        </div>

      </section>

    );

  }





  function openStandaloneCaseGenerator() {

    const key = "case-generator";

    setOpenTabs((prev) => (prev.some((tab) => tab.key === key) ? prev : [...prev, { key, label: "\u751f\u6210\u7528\u4f8b", type: "caseGenerator" }]));

    setActiveTabKey(key);

  }



  function renderCaseList() {

    const casePageCount = Math.max(1, Math.ceil(caseCount / casePagination.page_size));

    return renderCasesLayout(

      <>

        <section className="panel cases-toolbar-panel">

              <div className="cases-filter-row">

                <div className="cases-filter-group">

                  <input

                    className="cases-search-input"

                    value={caseFilters.keyword}

                    onChange={(event) => setCaseFilters((prev) => ({ ...prev, keyword: event.target.value }))}

                    placeholder="搜索用例名称/测试点"

                  />

                  <select

                    value={caseFilters.priority}

                    onChange={(event) => setCaseFilters((prev) => ({ ...prev, priority: event.target.value }))}

                  >

                    <option value="">筛选优先级</option>

                    {casePriorityOptions.map((item) => (

                      <option key={item.key} value={item.key}>

                        {`${item.key} - ${item.value}`}

                      </option>

                    ))}

                  </select>

                  <select

                    value={caseFilters.caseType}

                    onChange={(event) => setCaseFilters((prev) => ({ ...prev, caseType: event.target.value }))}

                  >

                    <option value="">筛选测试类型</option>

                    {caseTypeOptions.map((item) => (

                      <option key={item.key} value={item.key}>

                        {item.value}

                      </option>

                    ))}

                  </select>

                </div>

                <div className="cases-action-row">

                  <button type="button" className="btn ghost" onClick={openStandaloneCaseGenerator}>

                    生成用例

                  </button>

                  <button type="button" className="btn export" onClick={() => setShowCaseExportModal(true)}>

                    导出

                  </button>

                  <button type="button" className="btn action" onClick={() => openCaseEditor("create")}>

                    添加用例

                  </button>

                </div>

              </div>

        </section>



        <section className="panel cases-table-panel">

          <div className="cases-table-scroll">

            <table className="data-table cases-table">

              <thead>

                <tr>

                  <th>序号</th>

                  <th>测试点</th>

                  <th>用例名称</th>

                  <th>优先级</th>

                  <th>测试类型</th>

                  <th>所属模块</th>

                  <th>创建者</th>

                  <th>创建时间</th>

                  <th>操作</th>

                </tr>

              </thead>

              <tbody>

                {testCases.length === 0 && (

                  <tr>

                    <td colSpan={9} className="empty-cell">

                      暂无数据

                    </td>

                  </tr>

                )}

                {testCases.map((item, index) => (

                  <tr key={item.id}>

                    <td>{(casePagination.page - 1) * casePagination.page_size + index + 1}</td>

                    <td>{item.test_point || "-"}</td>

                    <td className="cases-title-cell">{item.title}</td>

                    <td>

                      {item.priority ? (

                        <span className={`priority-chip ${String(item.priority).toLowerCase()}`}>

                          {casePriorityLabelMap[item.priority] ? `${item.priority} - ${casePriorityLabelMap[item.priority]}` : item.priority}

                        </span>

                      ) : ""}

                    </td>

                    <td>{caseTypeOptions.find((option) => option.key === item.case_type)?.value || item.case_type_label || item.case_type || "-"}</td>

                    <td>{item.module_name || getModuleLabel(item.module_id) || getRequirementLabel(item.requirement_id) || "-"}</td>

                    <td>{item.creator || ""}</td>

                    <td>{(item.created_at || "").replace("T", " ").replace("Z", "") || "-"}</td>

                    <td>

                      <div className="cases-row-actions">

                        <button type="button" className="mini-btn" onClick={() => openCaseEditor("view", item)}>

                          查看

                        </button>

                        <button type="button" className="mini-btn primary" onClick={() => openCaseEditor("edit", item)}>

                          编辑

                        </button>

                        <button type="button" className="mini-btn danger" onClick={() => removeCaseItem(item.id)}>

                          删除

                        </button>

                      </div>

                    </td>

                  </tr>

                ))}

              </tbody>

            </table>

          </div>

          <div className="pagination">

            <div>{"共 "}{caseCount}{" 条"}</div>

            <div className="pagination-actions">

              <button

                className="btn ghost"

                disabled={casePagination.page <= 1}

                onClick={() => runSafe(() => loadTestCases({ page: casePagination.page - 1 }))}

              >

                {"上一页"}

              </button>

              <span>{casePagination.page} / {casePageCount}</span>

              <button

                className="btn ghost"

                disabled={casePagination.page >= casePageCount}

                onClick={() => runSafe(() => loadTestCases({ page: casePagination.page + 1 }))}

              >

                {"下一页"}

              </button>

              <select

                value={casePagination.page_size}

                onChange={(e) => runSafe(() => loadTestCases({ page: 1, page_size: Number(e.target.value) }))}

              >

                <option value={10}>{"10 条/页"}</option>

                <option value={20}>{"20 条/页"}</option>

                <option value={50}>{"50 条/页"}</option>

              </select>

            </div>

          </div>

        </section>

      </>

    );

  }



  function renderCaseEditor() {

    const readonly = caseEditorMode === "view";

    return renderCasesLayout(

      <>

        <section className="panel cases-editor-panel">

          <div className="cases-editor-header">

            <div className="cases-editor-header-left">

              <button type="button" className="back-link cases-back-link" onClick={closeCaseEditor}>

                ← 返回列表

              </button>

              <div className="cases-panel-title">{caseEditorMode === "edit" ? "编辑用例" : caseEditorMode === "view" ? "查看用例" : "新增用例"}</div>

              <div className="cases-panel-subtitle">按模块、步骤和预期结果维护结构化测试用例</div>

            </div>

          </div>



          <div className="cases-editor-form">

            <div className="cases-editor-row">

              <label className="cases-inline-field cases-inline-field-wide">

                <span>所属模块</span>

                <select value={caseForm.target_key || getCaseTargetValue(caseForm.requirement_id, caseForm.module_id)} onChange={(event) => handleCaseRequirementChange(event.target.value)} disabled={readonly}>

                  <option value="">请选择所属模块</option>

                  <optgroup label="需求类">

                    {requirementCaseTargets.map((item) => (

                      <option key={item.key} value={item.key}>

                        {item.label}

                      </option>

                    ))}

                  </optgroup>

                  <optgroup label="自定义分组">

                    {customCaseTargets.map((item) => (

                      <option key={item.key} value={item.key}>

                        {item.label}

                      </option>

                    ))}

                  </optgroup>

                </select>

              </label>

              <label className="cases-inline-field">

                <span>适用阶段</span>

                <select

                  value={caseForm.stage}

                  onChange={(event) => setCaseForm((prev) => ({ ...prev, stage: event.target.value }))}

                  disabled={readonly}

                >

                  <option value="">请选择适用阶段</option>

                  {CASE_STAGE_OPTIONS.map((item) => (

                    <option key={item} value={item}>

                      {item}

                    </option>

                  ))}

                </select>

              </label>

            </div>



            <div className="cases-editor-row">

              <label className="cases-inline-field">

                <span>用例类型</span>

                <select

                  value={caseForm.case_type}

                  onChange={(event) => setCaseForm((prev) => ({ ...prev, case_type: event.target.value }))}

                  disabled={readonly}

                >

                  <option value="">请选择用例类型</option>

                  {caseTypeOptions.map((item) => (

                    <option key={item.key} value={item.key}>

                      {item.value}

                    </option>

                  ))}

                </select>

              </label>

              <label className="cases-inline-field">

                <span>优先级</span>

                <select

                  value={caseForm.priority}

                  onChange={(event) => setCaseForm((prev) => ({ ...prev, priority: event.target.value }))}

                  disabled={readonly}

                >

                  <option value="">请选择优先级</option>

                  {casePriorityOptions.map((item) => (

                    <option key={item.key} value={item.key}>

                      {`${item.key} - ${item.value}`}

                    </option>

                  ))}

                </select>

              </label>

            </div>



            <label className="cases-inline-field cases-inline-field-block">

              <span>测试点</span>

              <input

                value={caseForm.test_point}

                onChange={(event) => setCaseForm((prev) => ({ ...prev, test_point: event.target.value }))}

                placeholder="请输入测试点"

                disabled={readonly}

              />

            </label>



            <label className="cases-inline-field cases-inline-field-block">

              <span>用例标题</span>

              <input

                value={caseForm.title}

                onChange={(event) => setCaseForm((prev) => ({ ...prev, title: event.target.value }))}

                placeholder="请输入用例标题"

                disabled={readonly}

              />

            </label>



            <label className="cases-inline-field cases-inline-field-block textarea-field">

              <span>前置条件</span>

              <textarea

                rows={4}

                value={caseForm.preconditions_text}

                onChange={(event) => setCaseForm((prev) => ({ ...prev, preconditions_text: event.target.value }))}

                placeholder="每行填写一条前置条件"

                disabled={readonly}

              />

            </label>



            <div className="cases-step-block">

              <div className="cases-step-head">

                <span>用例步骤</span>

                {!readonly && (

                  <button type="button" className="btn ghost small" onClick={() => appendCaseStep()}>

                    新增步骤

                  </button>

                )}

              </div>

              <table className="cases-step-table">

                <thead>

                  <tr>

                    <th className="serial-col">编号</th>

                    <th>步骤</th>

                    <th>预期</th>

                    <th className="action-col">操作</th>

                  </tr>

                </thead>

                <tbody>

                  {caseForm.steps.map((row, index) => (

                    <tr key={row.id}>

                      <td>{index + 1}</td>

                      <td>

                        <textarea

                          rows={2}

                          value={row.step}

                          onChange={(event) => updateCaseStepRow(row.id, "step", event.target.value)}

                          placeholder="请输入测试步骤"

                          disabled={readonly}

                        />

                      </td>

                      <td>

                        <textarea

                          rows={2}

                          value={row.expected}

                          onChange={(event) => updateCaseStepRow(row.id, "expected", event.target.value)}

                          placeholder="请输入预期结果"

                          disabled={readonly}

                        />

                      </td>

                      <td>

                        {!readonly && (

                          <div className="cases-step-actions">

                            <button type="button" className="row-icon-btn add" onClick={() => appendCaseStep(row.id)}>

                              新增

                            </button>

                            <button type="button" className="row-icon-btn copy" onClick={() => duplicateCaseStep(row.id)}>

                              复制

                            </button>

                            <button type="button" className="row-icon-btn danger" onClick={() => removeCaseStep(row.id)}>

                              删除

                            </button>

                          </div>

                        )}

                      </td>

                    </tr>

                  ))}

                </tbody>

              </table>

            </div>



            <div className="cases-editor-footer">

              {!readonly && (

                <button type="button" className="btn action cases-save-btn" onClick={submitCaseForm}>

                  保存

                </button>

              )}

              <button type="button" className="btn ghost cases-back-btn" onClick={closeCaseEditor}>

                返回

              </button>

            </div>

          </div>

        </section>

      </>,

      { editorMode: true }

    );

  }



  function renderPlaceholder(title, count) {

    return <section className="panel placeholder"><h3>{title}</h3><p>{`已接入基础数据，当前数量 ${count}`}</p><p>{"下一步可继续按同一风格完善该模块页面。"}</p></section>;

  }



  function renderActiveContent() {

    if (!activeTab) return null;

    if (activeTab.type === "review") return renderReviewPage(activeTab.requirementId);

    if (activeTab.type === "caseWorkflow") return <TestCaseWorkflowPage requirementId={activeTab.requirementId} onBack={() => setActiveTabKey("requirements")} onCasesChanged={loadCounts} />;

    if (activeTab.type === "caseGenerator") return <StandaloneCaseGeneratorPage onCasesChanged={loadCounts} onBack={() => { setOpenTabs((prev) => prev.filter((tab) => tab.key !== "case-generator")); setActiveTabKey("cases"); }} />;

    if (activeTab.key === "projects") return renderProjects();

    if (activeTab.key === "requirements") return renderRequirements();

    if (activeTab.key === "cases") return caseEditorMode === "list" ? renderCaseList() : renderCaseEditor();

    if (activeTab.key === "llmConfigs") return <LlmConfigPage />;

    if (activeTab.key === "prompts") return <PromptManagementPage />;

    return null;

  }



  return (

    <div className="layout">

      <header className="topbar"><div className="brand">AiTest</div><div className="project">{"演示项目 (Demo Project)"}</div><div className="top-actions"><span className={health === "ok" ? "status ok" : "status"}>{`后端: ${health}`}</span><a className="swagger-link" href="http://localhost:8001/swagger" target="_blank" rel="noreferrer">Swagger</a></div></header>

      <aside className="sidebar"><div className="menu-title">{"功能菜单"}</div><button className={activeTab?.key === "projects" ? "menu-btn active" : "menu-btn"} onClick={() => openModule("projects")}>{"项目管理"}</button><button className={activeTab?.key === "requirements" || activeTab?.type === "review" || activeTab?.type === "caseWorkflow" ? "menu-btn active" : "menu-btn"} onClick={() => openModule("requirements")}>{"需求管理"}</button><button className={activeTab?.key === "cases" || activeTab?.type === "caseGenerator" ? "menu-btn active" : "menu-btn"} onClick={() => openModule("cases")}>{"用例管理"}</button><button className={activeTab?.key === "llmConfigs" ? "menu-btn active" : "menu-btn"} onClick={() => openModule("llmConfigs")}>{"LLM配置"}</button><button className={activeTab?.key === "prompts" ? "menu-btn active" : "menu-btn"} onClick={() => openModule("prompts")}>{"提示词管理"}</button></aside>

      <main className="content"><div className="tab-strip">{openTabs.map((tab) => <button key={tab.key} className={activeTabKey === tab.key ? "strip-tab active" : "strip-tab"} onClick={() => setActiveTabKey(tab.key)}><span>{tab.label}</span>{openTabs.length > 1 && <span className="close" onClick={(e) => closeTab(tab.key, e)}>x</span>}</button>)}</div>{error && <div className="error-banner">{error}</div>}{renderActiveContent()}</main>



      {showProjectModal && <div className="modal-mask" onClick={() => setShowProjectModal(false)}><div className="modal-card compact" onClick={(e) => e.stopPropagation()}><div className="modal-header"><h3>{editingProjectId ? "编辑项目" : "新增项目"}</h3><button className="modal-close" onClick={() => setShowProjectModal(false)}>x</button></div><div className="modal-body"><label><span className="required">*</span>{"项目名称"}</label><input placeholder="请输入项目名称" value={projectForm.name} onChange={(e) => setProjectForm((prev) => ({ ...prev, name: e.target.value }))} /><label>{"项目描述"}</label><textarea rows={4} placeholder="请输入项目描述" value={projectForm.description} onChange={(e) => setProjectForm((prev) => ({ ...prev, description: e.target.value }))} /></div><div className="modal-footer"><button className="btn ghost" onClick={() => setShowProjectModal(false)}>{"取消"}</button><button className="btn action" onClick={submitProject} disabled={!projectForm.name}>{"确定"}</button></div></div></div>}



      {showReqImportModal && <div className="modal-mask" onClick={() => setShowReqImportModal(false)}><div className="modal-card requirement-modal" onClick={(e) => e.stopPropagation()}><div className="modal-header"><h3>{"上传需求文档"}</h3><button className="modal-close" onClick={() => setShowReqImportModal(false)}>x</button></div><div className="modal-body requirement-body"><label><span className="required">*</span>{"所属项目"}</label><select value={reqImportForm.project_id} onChange={(e) => setReqImportForm((prev) => ({ ...prev, project_id: e.target.value }))}>{projects.length === 0 && <option value="">{"请先创建项目"}</option>}{projects.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select><label>{"需求标题"}</label><input value={reqImportForm.title} placeholder="可选，不填时默认使用文档名称" onChange={(e) => setReqImportForm((prev) => ({ ...prev, title: e.target.value }))} /><label>{"上传方式"}</label><div className="radio-row"><label className="radio-item"><input type="radio" checked={reqImportForm.import_method === "file"} onChange={() => setReqImportForm((prev) => ({ ...prev, import_method: "file", jira_url: "" }))} /> {"上传文件"}</label><label className="radio-item"><input type="radio" checked={reqImportForm.import_method === "jira"} onChange={() => setReqImportForm((prev) => ({ ...prev, import_method: "jira" }))} /> {"Jira 链接"}</label></div>{reqImportForm.import_method === "file" ? <><label><span className="required">*</span>{"选择文件"}</label><label className="upload-dropzone"><input type="file" className="hidden-input" accept={importConfig.upload_extensions?.join(",") || ".pdf,.doc,.docx,.txt,.md"} onChange={(e) => handleImportFile(e.target.files?.[0] || null)} /><div className="upload-icon">{"上传"}</div><div className="upload-title">{"点击上传文件"}</div><div className="upload-desc">{"支持 PDF、Word(.doc/.docx)、TXT、Markdown"}</div>{reqImportFile && <div className="upload-file-name">{`已选择：${reqImportFile.name}`}</div>}</label></> : <><label><span className="required">*</span>{"Jira 链接"}</label><input value={reqImportForm.jira_url} placeholder="请输入 Jira Issue 或页面链接" onChange={(e) => setReqImportForm((prev) => ({ ...prev, jira_url: e.target.value }))} /><div className="policy-tip">{`允许域名：${importConfig.sources?.jira?.allowed_hosts?.join("、") || "未配置"}`}</div></>}</div><div className="modal-footer"><button className="btn ghost" onClick={() => setShowReqImportModal(false)}>{"取消"}</button><button className="btn action" onClick={submitRequirementImport} disabled={!reqImportForm.project_id || (reqImportForm.import_method === "file" ? !reqImportFile : !reqImportForm.jira_url)}>{"确定"}</button></div></div></div>}



      {showPreviewModal && previewData && <div className="modal-mask" onClick={() => setShowPreviewModal(false)}><div className="modal-card preview-modal" onClick={(e) => e.stopPropagation()}><div className="modal-header"><h3>{"需求预览"}</h3><button className="modal-close" onClick={() => setShowPreviewModal(false)}>x</button></div><div className="modal-body preview-body"><div className="preview-meta">{`标题：${previewData.title}`}</div>{previewData.preview_type === "html" && <div className="doc-html-preview" dangerouslySetInnerHTML={{ __html: previewData.preview_html || "" }} />}{previewData.preview_type === "text" && <pre className="preview-text">{previewData.preview_text || "暂无内容"}</pre>}{previewData.preview_type === "document" && <div className="preview-doc-block"><p>{`文件：${previewData.file_name}`}</p>{previewData.file_url.endsWith(".pdf") ? <iframe title="requirement-preview" src={`${ASSET_BASE_URL}${previewData.file_url}`} className="preview-frame" /> : <p>{"当前格式暂不支持完整保真预览，建议上传 `.docx` 以获得接近原文档的排版预览。"}</p>}{previewData.file_url && <a className="swagger-link" href={`${ASSET_BASE_URL}${previewData.file_url}`} target="_blank" rel="noreferrer">{"打开文件"}</a>}</div>}{previewData.preview_type === "link" && <div className="preview-doc-block"><p>{"来源：Jira 链接"}</p><a className="swagger-link" href={previewData.source_url} target="_blank" rel="noreferrer">{"打开 Jira"}</a></div>}</div></div></div>}



      {showCaseExportModal && (

        <div className="modal-mask" onClick={() => !exportingCases && setShowCaseExportModal(false)}>

          <div className="modal-card case-export-modal compact-export-modal" onClick={(e) => e.stopPropagation()}>

            <div className="modal-header compact-export-header">

              <h3>{"用例导出"}</h3>

              <button className="modal-close" onClick={() => !exportingCases && setShowCaseExportModal(false)}>x</button>

            </div>

            <div className="modal-body case-export-body compact-export-body">

              <label className="case-export-format-stack">

                <span>{"导出格式"}</span>

                <select

                  value={caseExportFormat}

                  onChange={(e) => {

                    const nextFormat = e.target.value;

                    setCaseExportFormat(nextFormat);

                    resetCaseExportConfig(nextFormat);

                  }}

                  disabled={exportingCases}

                >

                  <option value="excel">Excel</option>

                  <option value="word">Word</option>

                </select>

              </label>



              {caseExportFormat === "excel" && (

                <div className="case-export-config-panel compact-export-panel">

                  <div className="compact-export-panel-head">

                    <div>

                      <div className="case-export-panel-title">{"\u5bfc\u51fa\u5b57\u6bb5"}</div>

                      <div className="case-export-panel-desc">{"\u9009\u62e9\u9700\u8981\u5bfc\u51fa\u7684\u5b57\u6bb5\uff0c\u5e76\u652f\u6301\u62d6\u52a8\u6392\u5e8f\u3002"}</div>

                    </div>

                    <div className="compact-export-actions">

                      <div className="compact-export-dropdown">

                        <button

                          type="button"

                          className="btn ghost small compact-export-dropdown-btn"

                          onClick={() => setShowCaseExportFieldMenu((prev) => !prev)}

                          disabled={exportingCases}

                        >

                          {"?"}

                        </button>

                        {showCaseExportFieldMenu && (

                          <div className="compact-export-dropdown-menu">

                            {CASE_EXPORT_FIELD_COLUMNS.map((field) => {

                              const checked = caseExportFields.includes(field.key);

                              return (

                                <label key={field.key} className="compact-export-option">

                                  <input

                                    type="checkbox"

                                    checked={checked}

                                    onChange={() => toggleCaseExportField(field.key)}

                                    disabled={exportingCases}

                                  />

                                  <span>{field.label}</span>

                                </label>

                              );

                            })}

                          </div>

                        )}

                      </div>

                    </div>

                  </div>

                  <div className="case-export-selected-row compact-export-selected-row">

                    {getSelectedCaseExportColumns().map((field) => (

                      <div

                        key={field.key}

                        className={draggingCaseExportField === field.key ? "case-export-selected-chip dragging" : "case-export-selected-chip"}

                        draggable={!exportingCases}

                        onDragStart={() => setDraggingCaseExportField(field.key)}

                        onDragOver={(event) => event.preventDefault()}

                        onDrop={() => {

                          reorderCaseExportField(draggingCaseExportField, field.key);

                          setDraggingCaseExportField("");

                        }}

                        onDragEnd={() => setDraggingCaseExportField("")}

                      >

                        <span className="case-export-selected-chip-label">{field.label}</span>

                        <button

                          type="button"

                          className="case-export-selected-chip-remove"

                          onClick={() => toggleCaseExportField(field.key)}

                          disabled={exportingCases || caseExportFields.length <= 1}

                          aria-label={`\u79fb\u52a8${field.label}`}

                          title={`\u79fb\u52a8${field.label}`}

                        >

                          x

                        </button>

                      </div>

                    ))}

                  </div>

                </div>

              )}

            </div>

            <div className="modal-footer">

              <button className="btn ghost" onClick={() => setShowCaseExportModal(false)} disabled={exportingCases}>{"取消"}</button>

              <button className="btn action" onClick={submitCaseExport} disabled={exportingCases || caseExportFields.length === 0}>{exportingCases ? "导出中..." : "确认导出"}</button>

            </div>

          </div>

        </div>

      )}



      {showCaseModuleModal && (

        <div className="modal-mask" onClick={() => setShowCaseModuleModal(false)}>

          <div className="modal-card compact case-module-modal" onClick={(e) => e.stopPropagation()}>

            <div className="modal-header">

              <h3>{editingCaseModuleId ? "编辑分组" : "新增分组"}</h3>

              <button className="modal-close" onClick={() => setShowCaseModuleModal(false)}>x</button>

            </div>

            <div className="modal-body">

              <label>上级</label>

              <select value={caseModuleForm.parent_id} onChange={(e) => setCaseModuleForm((prev) => ({ ...prev, parent_id: e.target.value }))}>

                <option value="">无</option>

                {caseModules.map((item) => (

                  <option key={item.id} value={item.id}>

                    {item.name}

                  </option>

                ))}

              </select>

              <label><span className="required">*</span>分组名称</label>

              <input

                value={caseModuleForm.name}

                placeholder="请输入"

                onChange={(e) => setCaseModuleForm((prev) => ({ ...prev, name: e.target.value }))}

              />

            </div>

            <div className="modal-footer">

              <button className="btn ghost" onClick={() => setShowCaseModuleModal(false)}>取消</button>

              <button className="btn action" onClick={submitCaseModule} disabled={!caseModuleForm.name.trim()}>确定</button>

            </div>

          </div>

        </div>

      )}

    </div>

  );

}



export default App;

