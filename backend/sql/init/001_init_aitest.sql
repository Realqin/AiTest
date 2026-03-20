CREATE DATABASE IF NOT EXISTS aitest CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE aitest;

CREATE TABLE IF NOT EXISTS id_sequences (
  scope VARCHAR(64) PRIMARY KEY,
  current_value INT NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS projects (
  id VARCHAR(64) PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  description TEXT NOT NULL,
  creator VARCHAR(50) NOT NULL DEFAULT 'admin',
  created_at DATETIME NULL,
  updated_at DATETIME NULL,
  extra_data JSON NOT NULL,
  KEY idx_projects_name (name),
  KEY idx_projects_creator (creator)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS requirements (
  id VARCHAR(64) PRIMARY KEY,
  title VARCHAR(200) NOT NULL,
  body_text LONGTEXT NOT NULL,
  project_id VARCHAR(64) NOT NULL DEFAULT '',
  project VARCHAR(100) NOT NULL DEFAULT 'Demo Project',
  status VARCHAR(50) NOT NULL DEFAULT 'draft',
  creator VARCHAR(50) NOT NULL DEFAULT 'admin',
  summary VARCHAR(500) NOT NULL DEFAULT '',
  start_date VARCHAR(32) NULL,
  end_date VARCHAR(32) NULL,
  created_date VARCHAR(10) NOT NULL DEFAULT '',
  version INT NOT NULL DEFAULT 1,
  import_method VARCHAR(20) NOT NULL DEFAULT 'manual',
  source_name VARCHAR(200) NOT NULL DEFAULT '',
  source_url VARCHAR(1000) NOT NULL DEFAULT '',
  file_name VARCHAR(255) NOT NULL DEFAULT '',
  stored_file_name VARCHAR(255) NOT NULL DEFAULT '',
  preview_type VARCHAR(20) NOT NULL DEFAULT 'text',
  preview_html LONGTEXT NOT NULL,
  review_status VARCHAR(20) NOT NULL DEFAULT 'pending',
  latest_review_run_id VARCHAR(64) NULL,
  created_at DATETIME NULL,
  updated_at DATETIME NULL,
  extra_data JSON NOT NULL,
  KEY idx_requirements_title (title),
  KEY idx_requirements_project_id (project_id),
  KEY idx_requirements_project (project),
  KEY idx_requirements_status (status),
  KEY idx_requirements_creator (creator),
  KEY idx_requirements_import_method (import_method),
  KEY idx_requirements_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS test_cases (
  id VARCHAR(64) PRIMARY KEY,
  requirement_id VARCHAR(64) NOT NULL,
  title VARCHAR(200) NOT NULL,
  test_point VARCHAR(200) NOT NULL DEFAULT '',
  preconditions JSON NOT NULL,
  steps JSON NOT NULL,
  expected JSON NOT NULL,
  priority VARCHAR(10) NOT NULL DEFAULT 'P2',
  case_type VARCHAR(64) NOT NULL DEFAULT '',
  module_id VARCHAR(64) NOT NULL DEFAULT '',
  stage VARCHAR(50) NOT NULL DEFAULT '',
  review_status VARCHAR(20) NOT NULL DEFAULT '',
  creator VARCHAR(50) NOT NULL DEFAULT 'admin',
  source VARCHAR(20) NOT NULL DEFAULT '',
  version INT NOT NULL DEFAULT 1,
  created_at DATETIME NULL,
  updated_at DATETIME NULL,
  extra_data JSON NOT NULL,
  KEY idx_test_cases_requirement_id (requirement_id),
  KEY idx_test_cases_title (title),
  KEY idx_test_cases_priority (priority),
  KEY idx_test_cases_case_type (case_type),
  KEY idx_test_cases_module_id (module_id),
  KEY idx_test_cases_stage (stage),
  KEY idx_test_cases_creator (creator),
  CONSTRAINT fk_test_cases_requirement FOREIGN KEY (requirement_id) REFERENCES requirements(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS agent_configs (
  id VARCHAR(64) PRIMARY KEY,
  role VARCHAR(100) NOT NULL,
  prompt_template LONGTEXT NOT NULL,
  model_policy VARCHAR(50) NOT NULL DEFAULT 'balanced',
  enabled TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NULL,
  updated_at DATETIME NULL,
  extra_data JSON NOT NULL,
  KEY idx_agent_configs_role (role),
  KEY idx_agent_configs_enabled (enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS llm_configs (
  id VARCHAR(64) PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  api_url VARCHAR(500) NOT NULL,
  api_key VARCHAR(500) NOT NULL,
  model_name VARCHAR(100) NOT NULL,
  context_limit INT NOT NULL DEFAULT 128000,
  vision_enabled TINYINT(1) NOT NULL DEFAULT 0,
  stream_enabled TINYINT(1) NOT NULL DEFAULT 1,
  enabled TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME NULL,
  updated_at DATETIME NULL,
  extra_data JSON NOT NULL,
  KEY idx_llm_configs_name (name),
  KEY idx_llm_configs_model_name (model_name),
  KEY idx_llm_configs_enabled (enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS prompt_templates (
  id VARCHAR(64) PRIMARY KEY,
  prompt_type VARCHAR(50) NOT NULL,
  name VARCHAR(100) NOT NULL,
  description VARCHAR(500) NOT NULL DEFAULT '',
  content LONGTEXT NOT NULL,
  remark VARCHAR(200) NOT NULL DEFAULT '',
  enabled TINYINT(1) NOT NULL DEFAULT 1,
  is_default TINYINT(1) NOT NULL DEFAULT 0,
  is_preset TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME NULL,
  updated_at DATETIME NULL,
  extra_data JSON NOT NULL,
  KEY idx_prompt_templates_prompt_type (prompt_type),
  KEY idx_prompt_templates_name (name),
  KEY idx_prompt_templates_enabled (enabled),
  KEY idx_prompt_templates_is_default (is_default)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS dictionaries (
  id VARCHAR(64) PRIMARY KEY,
  `group` VARCHAR(100) NOT NULL DEFAULT '',
  `key` VARCHAR(100) NOT NULL,
  value VARCHAR(200) NOT NULL DEFAULT '',
  sort_order INT NOT NULL DEFAULT 0,
  enabled TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NULL,
  updated_at DATETIME NULL,
  extra_data JSON NOT NULL,
  KEY idx_dictionaries_group (`group`),
  KEY idx_dictionaries_key (`key`),
  KEY idx_dictionaries_enabled (enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS mcp_tools (
  id VARCHAR(64) PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  description TEXT NOT NULL,
  endpoint VARCHAR(1000) NOT NULL,
  created_at DATETIME NULL,
  updated_at DATETIME NULL,
  extra_data JSON NOT NULL,
  KEY idx_mcp_tools_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS review_runs (
  id VARCHAR(64) PRIMARY KEY,
  requirement_id VARCHAR(64) NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'running',
  progress INT NOT NULL DEFAULT 0,
  current_step INT NOT NULL DEFAULT 0,
  model VARCHAR(100) NOT NULL DEFAULT '',
  route_reason VARCHAR(500) NOT NULL DEFAULT '',
  llm_config_id VARCHAR(64) NULL,
  prompt_template_name VARCHAR(500) NOT NULL DEFAULT '',
  checks JSON NOT NULL,
  results JSON NOT NULL,
  check_prompt_map JSON NOT NULL,
  started_at DATETIME NULL,
  finished_at DATETIME NULL,
  created_at DATETIME NULL,
  updated_at DATETIME NULL,
  extra_data JSON NOT NULL,
  KEY idx_review_runs_requirement_id (requirement_id),
  KEY idx_review_runs_status (status),
  KEY idx_review_runs_llm_config_id (llm_config_id),
  KEY idx_review_runs_created_at (created_at),
  CONSTRAINT fk_review_runs_requirement FOREIGN KEY (requirement_id) REFERENCES requirements(id) ON DELETE CASCADE,
  CONSTRAINT fk_review_runs_llm_config FOREIGN KEY (llm_config_id) REFERENCES llm_configs(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS requirement_versions (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  requirement_id VARCHAR(64) NOT NULL,
  position INT NOT NULL,
  version INT NOT NULL,
  content LONGTEXT NOT NULL,
  created_at DATETIME NULL,
  extra_data JSON NOT NULL,
  KEY idx_requirement_versions_requirement_id (requirement_id),
  CONSTRAINT fk_requirement_versions_requirement FOREIGN KEY (requirement_id) REFERENCES requirements(id) ON DELETE CASCADE,
  CONSTRAINT uq_requirement_versions_requirement_position UNIQUE (requirement_id, position)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS requirement_reviews (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  requirement_id VARCHAR(64) NOT NULL,
  position INT NOT NULL,
  run_id VARCHAR(64) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_requirement_reviews_requirement_id (requirement_id),
  KEY idx_requirement_reviews_run_id (run_id),
  CONSTRAINT fk_requirement_reviews_requirement FOREIGN KEY (requirement_id) REFERENCES requirements(id) ON DELETE CASCADE,
  CONSTRAINT fk_requirement_reviews_run FOREIGN KEY (run_id) REFERENCES review_runs(id) ON DELETE CASCADE,
  CONSTRAINT uq_requirement_reviews_requirement_position UNIQUE (requirement_id, position)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
