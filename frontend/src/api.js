const BASE_URL = "http://localhost:8001";

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, options);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const ASSET_BASE_URL = BASE_URL;

export async function getHealth() {
  return request("/health");
}

export async function getDictionaries(group = "") {
  const query = group ? `?group=${encodeURIComponent(group)}` : "";
  return request(`/api/dictionaries${query}`);
}

export async function getProjects(params = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  });
  const query = search.toString() ? `?${search.toString()}` : "";
  return request(`/api/projects${query}`);
}

export async function createProject(payload) {
  return request("/api/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function updateProject(id, payload) {
  return request(`/api/projects/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function deleteProject(id) {
  return request(`/api/projects/${id}`, { method: "DELETE" });
}

export async function getRequirementImportConfig() {
  return request("/api/requirements/import-config");
}

export async function getRequirements(params = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  });
  const query = search.toString() ? `?${search.toString()}` : "";
  return request(`/api/requirements${query}`);
}

export async function importRequirement(formData) {
  const res = await fetch(`${BASE_URL}/api/requirements/import`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed: ${res.status}`);
  }
  return res.json();
}

export async function getRequirementPreview(id) {
  return request(`/api/requirements/${id}/preview`);
}

export async function updateRequirement(id, payload) {
  return request(`/api/requirements/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function deleteRequirement(id) {
  return request(`/api/requirements/${id}`, { method: "DELETE" });
}

export async function bulkDeleteRequirements(ids) {
  return request("/api/requirements/bulk-delete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ids }),
  });
}

export async function getReviewChecks() {
  return request("/api/ai/reviews/checks");
}

export async function startRequirementReview(payload) {
  return request("/api/ai/reviews/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function getReviewRun(runId) {
  return request(`/api/ai/reviews/${runId}`);
}

export async function getReviewRunStatus(runId) {
  return request(`/api/ai/reviews/${runId}/status`);
}

export async function getRequirementReviews(requirementId) {
  return request(`/api/ai/reviews/by-requirement/${requirementId}`);
}

export async function getTestCases(params = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  });
  const query = search.toString() ? `?${search.toString()}` : "";
  return request(`/api/test-cases${query}`);
}

export async function getTestCaseSidebar() {
  return request("/api/test-cases/sidebar");
}

export async function createTestCase(payload) {
  return request("/api/test-cases", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function updateTestCase(caseId, payload) {
  return request(`/api/test-cases/${caseId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function deleteTestCase(caseId) {
  return request(`/api/test-cases/${caseId}`, {
    method: "DELETE",
  });
}

export async function getTestCaseModules() {
  return request("/api/test-cases/modules");
}

export async function createTestCaseModule(payload) {
  return request("/api/test-cases/modules", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function updateTestCaseModule(moduleId, payload) {
  return request(`/api/test-cases/modules/${moduleId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function deleteTestCaseModule(moduleId) {
  return request(`/api/test-cases/modules/${moduleId}`, {
    method: "DELETE",
  });
}

export async function getTestCaseWorkflow(requirementId) {
  return request(`/api/test-cases/workflow/${requirementId}`);
}

export async function updateTestCaseWorkflowDraft(requirementId, payload) {
  return request(`/api/test-cases/workflow/${requirementId}/draft`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function generateTestCaseWorkflowStage(requirementId, payload) {
  return request(`/api/test-cases/workflow/${requirementId}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function saveTestCaseWorkflowSnapshot(requirementId, payload) {
  return request(`/api/test-cases/workflow/${requirementId}/snapshot`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function confirmTestCaseWorkflowStage(requirementId, payload) {
  return request(`/api/test-cases/workflow/${requirementId}/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function rollbackTestCaseWorkflowStage(requirementId, payload) {
  return request(`/api/test-cases/workflow/${requirementId}/rollback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function getStandaloneCaseGeneratorConfig() {
  return request("/api/test-cases/generator/config");
}

export async function generateStandaloneCaseGenerator(payload) {
  return request("/api/test-cases/generator/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function getAgentConfigs() {
  return request("/api/agents");
}

export async function getLlmConfigs() {
  return request("/api/llm-configs");
}

export async function createLlmConfig(payload) {
  return request("/api/llm-configs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function updateLlmConfig(id, payload) {
  return request(`/api/llm-configs/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function toggleLlmConfig(id, enabled) {
  return request(`/api/llm-configs/${id}/toggle`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled }),
  });
}

export async function deleteLlmConfig(id) {
  return request(`/api/llm-configs/${id}`, { method: "DELETE" });
}

export async function testLlmConnection(payload) {
  return request("/api/llm-configs/test-connection", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function fetchLlmModels(payload) {
  return request("/api/llm-configs/models", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function getPromptTemplates() {
  return request("/api/prompts");
}

export async function createPromptTemplate(payload) {
  return request("/api/prompts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function updatePromptTemplate(id, payload) {
  return request(`/api/prompts/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function togglePromptTemplate(id, enabled) {
  return request(`/api/prompts/${id}/toggle`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled }),
  });
}

export async function deletePromptTemplate(id) {
  return request(`/api/prompts/${id}`, { method: "DELETE" });
}
