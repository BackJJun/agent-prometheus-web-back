-- Prometheus database initialization script.
-- Source of truth for local/backend database bootstrap.
-- Execution order: common schema -> web schema -> plugin schema.

-- Prometheus common database schema.
-- Shared by web, plugin, bridge, and dashboard aggregation.
-- Authentication is handled by Keycloak. This DB stores internal user mapping,
-- workspace authorization, repositories, and dashboard aggregates.

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS organizations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  slug TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'inactive', 'deleted')),
  payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
  email TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  avatar_url TEXT,
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'inactive', 'deleted')),
  last_login_at TIMESTAMPTZ,
  payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_auth_identities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  provider TEXT NOT NULL DEFAULT 'keycloak'
    CHECK (provider IN ('keycloak')),
  issuer TEXT NOT NULL,
  subject TEXT NOT NULL,
  preferred_username TEXT,
  email TEXT,
  email_verified BOOLEAN,
  claims JSONB,
  first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (provider, issuer, subject),
  UNIQUE (user_id, provider, issuer)
);

CREATE TABLE IF NOT EXISTS user_login_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  auth_identity_id UUID REFERENCES user_auth_identities(id) ON DELETE SET NULL,
  provider TEXT NOT NULL DEFAULT 'keycloak'
    CHECK (provider IN ('keycloak')),
  issuer TEXT,
  subject TEXT,
  event_type TEXT NOT NULL
    CHECK (event_type IN ('login_success', 'login_failure', 'logout', 'token_refresh', 'token_rejected')),
  ip_address INET,
  user_agent TEXT,
  reason TEXT,
  payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS workspaces (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  slug TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'archived', 'deleted')),
  created_by UUID REFERENCES users(id) ON DELETE SET NULL,
  payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (org_id, slug)
);

CREATE TABLE IF NOT EXISTS roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  is_system BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (org_id, name)
);

CREATE TABLE IF NOT EXISTS workspace_members (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role_id UUID REFERENCES roles(id) ON DELETE SET NULL,
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'invited', 'disabled')),
  joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, user_id)
);

CREATE TABLE IF NOT EXISTS repositories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID REFERENCES workspaces(id) ON DELETE SET NULL,
  provider TEXT NOT NULL
    CHECK (provider IN ('github', 'gitlab', 'gitea', 'local', 'unknown')),
  name TEXT NOT NULL,
  full_name TEXT NOT NULL,
  default_branch TEXT NOT NULL DEFAULT 'main',
  description TEXT,
  clone_url TEXT,
  web_url TEXT,
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'archived', 'deleted', 'unknown')),
  last_synced_at TIMESTAMPTZ,
  payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (provider, full_name)
);

CREATE TABLE IF NOT EXISTS dashboard_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scope TEXT NOT NULL CHECK (scope IN ('global', 'org', 'workspace', 'user')),
  scope_id TEXT,
  total_web_sessions INT NOT NULL DEFAULT 0,
  total_plg_tasks INT NOT NULL DEFAULT 0,
  today_web_sessions INT NOT NULL DEFAULT 0,
  today_plg_tasks INT NOT NULL DEFAULT 0,
  total_workspaces INT NOT NULL DEFAULT 0,
  total_file_edits INT NOT NULL DEFAULT 0,
  total_tool_calls INT NOT NULL DEFAULT 0,
  recent_error_count INT NOT NULL DEFAULT 0,
  last_plg_sync_at TIMESTAMPTZ,
  last_session_at TIMESTAMPTZ,
  payload JSONB,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS dashboard_daily_stats (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  stat_date DATE NOT NULL,
  scope TEXT NOT NULL DEFAULT 'global'
    CHECK (scope IN ('global', 'org', 'workspace', 'user')),
  scope_id TEXT,
  web_sessions_count INT NOT NULL DEFAULT 0,
  plg_tasks_count INT NOT NULL DEFAULT 0,
  active_workspaces_count INT NOT NULL DEFAULT 0,
  total_messages INT NOT NULL DEFAULT 0,
  tool_calls INT NOT NULL DEFAULT 0,
  file_edits INT NOT NULL DEFAULT 0,
  command_runs INT NOT NULL DEFAULT 0,
  error_count INT NOT NULL DEFAULT 0,
  tokens_in BIGINT NOT NULL DEFAULT 0,
  tokens_out BIGINT NOT NULL DEFAULT 0,
  total_cost NUMERIC(12, 6) NOT NULL DEFAULT 0,
  payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_users_org_status
  ON users (org_id, status);


CREATE INDEX IF NOT EXISTS idx_user_auth_identities_email
  ON user_auth_identities (email)
  WHERE email IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_user_login_events_user
  ON user_login_events (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_workspaces_org_status
  ON workspaces (org_id, status);

CREATE INDEX IF NOT EXISTS idx_repositories_workspace
  ON repositories (workspace_id, provider, status);

CREATE UNIQUE INDEX IF NOT EXISTS uq_dashboard_snapshots_global
  ON dashboard_snapshots (scope)
  WHERE scope_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_dashboard_snapshots_scoped
  ON dashboard_snapshots (scope, scope_id)
  WHERE scope_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_dashboard_daily_stats_global
  ON dashboard_daily_stats (stat_date, scope)
  WHERE scope_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_dashboard_daily_stats_scoped
  ON dashboard_daily_stats (stat_date, scope, scope_id)
  WHERE scope_id IS NOT NULL;

-- Additional lookup indexes
CREATE INDEX IF NOT EXISTS idx_workspace_members_user
  ON workspace_members (user_id, status);

CREATE INDEX IF NOT EXISTS idx_workspace_members_role
  ON workspace_members (role_id)
  WHERE role_id IS NOT NULL;


CREATE INDEX IF NOT EXISTS idx_dashboard_snapshots_updated
  ON dashboard_snapshots (updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_dashboard_daily_stats_scope_date
  ON dashboard_daily_stats (scope, scope_id, stat_date DESC);

-- Additional audit lookup indexes
CREATE INDEX IF NOT EXISTS idx_user_login_events_identity
  ON user_login_events (auth_identity_id, created_at DESC)
  WHERE auth_identity_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_user_login_events_subject
  ON user_login_events (issuer, subject, created_at DESC)
  WHERE issuer IS NOT NULL AND subject IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_user_login_events_type
  ON user_login_events (event_type, created_at DESC);

-- ============================================================================
-- Web schema
-- ============================================================================

-- Prometheus web database schema.
-- Depends on common_db.txt.
-- Web owns web chat, document/RAG, repository provider view, settings,
-- monitoring, and LLM model configuration.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  file_name TEXT NOT NULL,
  file_type TEXT NOT NULL,
  mime_type TEXT,
  storage_uri TEXT NOT NULL,
  visibility TEXT NOT NULL DEFAULT 'workspace'
    CHECK (visibility IN ('private', 'workspace', 'org', 'public')),
  owner_id UUID REFERENCES users(id) ON DELETE SET NULL,
  indexing_status TEXT NOT NULL DEFAULT 'pending'
    CHECK (indexing_status IN ('pending', 'indexing', 'indexed', 'failed')),
  latest_version_id UUID,
  payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS document_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  version_no INT NOT NULL,
  storage_uri TEXT NOT NULL,
  file_size_bytes BIGINT,
  checksum_sha256 TEXT,
  parser_name TEXT,
  parser_version TEXT,
  chunk_count INT NOT NULL DEFAULT 0,
  token_count INT NOT NULL DEFAULT 0,
  created_by UUID REFERENCES users(id) ON DELETE SET NULL,
  payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (document_id, version_no)
);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'fk_documents_latest_version'
  ) THEN
    ALTER TABLE documents
      ADD CONSTRAINT fk_documents_latest_version
      FOREIGN KEY (latest_version_id)
      REFERENCES document_versions(id)
      ON DELETE SET NULL
      DEFERRABLE INITIALLY DEFERRED;
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS document_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  version_id UUID NOT NULL REFERENCES document_versions(id) ON DELETE CASCADE,
  chunk_index INT NOT NULL,
  heading TEXT,
  content TEXT NOT NULL,
  token_count INT NOT NULL DEFAULT 0,
  embedding_id TEXT,
  payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (document_id, version_id, chunk_index)
);

CREATE TABLE IF NOT EXISTS document_index_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
  version_id UUID REFERENCES document_versions(id) ON DELETE SET NULL,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
  current_step TEXT,
  progress INT NOT NULL DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  error_message TEXT,
  payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS document_index_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id UUID NOT NULL REFERENCES document_index_jobs(id) ON DELETE CASCADE,
  level TEXT NOT NULL DEFAULT 'info'
    CHECK (level IN ('debug', 'info', 'warn', 'error')),
  step TEXT,
  message TEXT NOT NULL,
  payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS document_permissions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  principal_type TEXT NOT NULL
    CHECK (principal_type IN ('user', 'role', 'workspace', 'org')),
  principal_id UUID NOT NULL,
  permission TEXT NOT NULL
    CHECK (permission IN ('read', 'write', 'admin')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (document_id, principal_type, principal_id, permission)
);

CREATE TABLE IF NOT EXISTS repository_providers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  provider TEXT NOT NULL CHECK (provider IN ('github', 'gitlab', 'gitea')),
  name TEXT NOT NULL,
  base_url TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'inactive', 'error')),
  last_synced_at TIMESTAMPTZ,
  config JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, provider, name)
);

CREATE TABLE IF NOT EXISTS repository_groups (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  provider_id UUID NOT NULL REFERENCES repository_providers(id) ON DELETE CASCADE,
  provider_group_id TEXT,
  name TEXT NOT NULL,
  full_path TEXT NOT NULL,
  parent_group_id UUID REFERENCES repository_groups(id) ON DELETE SET NULL,
  visibility TEXT CHECK (visibility IN ('private', 'internal', 'public')),
  last_synced_at TIMESTAMPTZ,
  payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (provider_id, full_path)
);

CREATE TABLE IF NOT EXISTS repository_connections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
  provider_id UUID NOT NULL REFERENCES repository_providers(id) ON DELETE CASCADE,
  group_id UUID REFERENCES repository_groups(id) ON DELETE SET NULL,
  provider_repository_id TEXT,
  name TEXT NOT NULL,
  full_name TEXT NOT NULL,
  default_branch TEXT,
  clone_url TEXT,
  web_url TEXT,
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'archived', 'disabled', 'error')),
  last_synced_at TIMESTAMPTZ,
  payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (provider_id, full_name)
);

CREATE TABLE IF NOT EXISTS repository_branches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  connection_id UUID NOT NULL REFERENCES repository_connections(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  commit_sha TEXT,
  is_default BOOLEAN NOT NULL DEFAULT false,
  protected BOOLEAN NOT NULL DEFAULT false,
  last_synced_at TIMESTAMPTZ,
  payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (connection_id, name)
);

CREATE TABLE IF NOT EXISTS repository_commits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  connection_id UUID NOT NULL REFERENCES repository_connections(id) ON DELETE CASCADE,
  branch_name TEXT,
  commit_sha TEXT NOT NULL,
  parent_shas TEXT[] NOT NULL DEFAULT '{}',
  author_name TEXT,
  author_email TEXT,
  committed_at TIMESTAMPTZ,
  message TEXT NOT NULL,
  web_url TEXT,
  payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (connection_id, commit_sha)
);

CREATE TABLE IF NOT EXISTS code_index_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  repository_id UUID REFERENCES repositories(id) ON DELETE CASCADE,
  connection_id UUID REFERENCES repository_connections(id) ON DELETE SET NULL,
  branch_name TEXT NOT NULL,
  commit_sha TEXT,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
  current_step TEXT,
  progress INT NOT NULL DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  error_message TEXT,
  payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS code_index_files (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id UUID NOT NULL REFERENCES code_index_jobs(id) ON DELETE CASCADE,
  repository_id UUID REFERENCES repositories(id) ON DELETE CASCADE,
  path TEXT NOT NULL,
  language TEXT,
  commit_sha TEXT,
  token_count INT NOT NULL DEFAULT 0,
  line_count INT NOT NULL DEFAULT 0,
  embedding_id TEXT,
  payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (job_id, path)
);

CREATE TABLE IF NOT EXISTS web_chat_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  title TEXT NOT NULL,
  mode TEXT NOT NULL DEFAULT 'chat'
    CHECK (mode IN ('chat', 'rag', 'code')),
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'archived', 'deleted')),
  selected_model_id UUID,
  last_message_at TIMESTAMPTZ,
  payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS web_chat_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES web_chat_sessions(id) ON DELETE CASCADE,
  parent_message_id UUID REFERENCES web_chat_messages(id) ON DELETE SET NULL,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
  content TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'completed'
    CHECK (status IN ('pending', 'streaming', 'completed', 'failed')),
  token_count INT NOT NULL DEFAULT 0,
  payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS web_chat_references (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id UUID NOT NULL REFERENCES web_chat_messages(id) ON DELETE CASCADE,
  source_type TEXT NOT NULL
    CHECK (source_type IN ('document', 'document_chunk', 'repository', 'code_file', 'commit', 'plugin_task')),
  source_id UUID,
  title TEXT,
  excerpt TEXT,
  score NUMERIC(8, 6),
  payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS web_chat_attachments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES web_chat_sessions(id) ON DELETE CASCADE,
  message_id UUID REFERENCES web_chat_messages(id) ON DELETE SET NULL,
  file_name TEXT NOT NULL,
  mime_type TEXT,
  storage_uri TEXT NOT NULL,
  file_size_bytes BIGINT,
  payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS web_tool_calls (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES web_chat_sessions(id) ON DELETE CASCADE,
  message_id UUID REFERENCES web_chat_messages(id) ON DELETE SET NULL,
  tool_name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
  input JSONB,
  output JSONB,
  error_message TEXT,
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS api_keys (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  key_hash TEXT NOT NULL UNIQUE,
  scopes TEXT[] NOT NULL DEFAULT '{}',
  last_used_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ,
  revoked_at TIMESTAMPTZ,
  created_by UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS notification_settings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  channel TEXT NOT NULL CHECK (channel IN ('email', 'slack', 'webhook')),
  enabled BOOLEAN NOT NULL DEFAULT true,
  target TEXT,
  events TEXT[] NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS service_health_checks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
  service_name TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('healthy', 'degraded', 'down')),
  latency_ms INT,
  error_rate NUMERIC(8, 4),
  checked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  payload JSONB
);

CREATE TABLE IF NOT EXISTS monitoring_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
  level TEXT NOT NULL CHECK (level IN ('debug', 'info', 'warn', 'error')),
  service TEXT NOT NULL,
  message TEXT NOT NULL,
  detail TEXT,
  payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS llm_providers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  base_url TEXT,
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'inactive', 'error')),
  config JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, provider)
);

CREATE TABLE IF NOT EXISTS llm_models (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  provider_id UUID NOT NULL REFERENCES llm_providers(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  model_key TEXT NOT NULL,
  context_window INT,
  enabled BOOLEAN NOT NULL DEFAULT true,
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'inactive', 'deprecated')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (provider_id, model_key)
);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'fk_web_chat_sessions_selected_model'
  ) THEN
    ALTER TABLE web_chat_sessions
      ADD CONSTRAINT fk_web_chat_sessions_selected_model
      FOREIGN KEY (selected_model_id)
      REFERENCES llm_models(id)
      ON DELETE SET NULL;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_documents_workspace_status
  ON documents (workspace_id, indexing_status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_document_chunks_version
  ON document_chunks (version_id, chunk_index);

CREATE INDEX IF NOT EXISTS idx_repository_connections_workspace
  ON repository_connections (workspace_id, provider_id, status);

CREATE INDEX IF NOT EXISTS idx_repository_commits_connection
  ON repository_commits (connection_id, committed_at DESC);

CREATE INDEX IF NOT EXISTS idx_code_index_jobs_workspace
  ON code_index_jobs (workspace_id, status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_web_chat_sessions_workspace
  ON web_chat_sessions (workspace_id, status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_web_chat_messages_session
  ON web_chat_messages (session_id, created_at);

CREATE INDEX IF NOT EXISTS idx_web_chat_references_message
  ON web_chat_references (message_id, source_type);

CREATE INDEX IF NOT EXISTS idx_monitoring_events_workspace
  ON monitoring_events (workspace_id, level, created_at DESC);

-- Additional lookup indexes

CREATE INDEX IF NOT EXISTS idx_document_index_jobs_document
  ON document_index_jobs (document_id, status, created_at DESC)
  WHERE document_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_document_index_events_job
  ON document_index_events (job_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_document_permissions_principal
  ON document_permissions (principal_type, principal_id, permission);

CREATE INDEX IF NOT EXISTS idx_repository_providers_workspace
  ON repository_providers (workspace_id, provider, status);


CREATE INDEX IF NOT EXISTS idx_repository_branches_connection
  ON repository_branches (connection_id, is_default DESC, name);


CREATE INDEX IF NOT EXISTS idx_code_index_files_repository
  ON code_index_files (repository_id, path)
  WHERE repository_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_web_chat_messages_role
  ON web_chat_messages (session_id, role, created_at);

CREATE INDEX IF NOT EXISTS idx_web_chat_attachments_session
  ON web_chat_attachments (session_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_web_tool_calls_message
  ON web_tool_calls (message_id, status, created_at DESC)
  WHERE message_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_api_keys_workspace
  ON api_keys (workspace_id, revoked_at, expires_at);

CREATE INDEX IF NOT EXISTS idx_notification_settings_workspace
  ON notification_settings (workspace_id, channel, enabled);

CREATE INDEX IF NOT EXISTS idx_service_health_checks_latest
  ON service_health_checks (workspace_id, service_name, checked_at DESC);

CREATE INDEX IF NOT EXISTS idx_llm_providers_workspace
  ON llm_providers (workspace_id, status);

CREATE INDEX IF NOT EXISTS idx_llm_models_provider
  ON llm_models (provider_id, enabled, status);

-- Additional web relation lookup indexes
CREATE INDEX IF NOT EXISTS idx_documents_owner
  ON documents (owner_id, updated_at DESC)
  WHERE owner_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_document_index_jobs_version
  ON document_index_jobs (version_id, status, created_at DESC)
  WHERE version_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_repository_connections_repository
  ON repository_connections (repository_id, status);

CREATE INDEX IF NOT EXISTS idx_repository_connections_group
  ON repository_connections (group_id, status)
  WHERE group_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_repository_commits_branch
  ON repository_commits (connection_id, branch_name, committed_at DESC)
  WHERE branch_name IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_code_index_jobs_repository
  ON code_index_jobs (repository_id, branch_name, created_at DESC)
  WHERE repository_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_code_index_jobs_connection
  ON code_index_jobs (connection_id, branch_name, created_at DESC)
  WHERE connection_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_web_chat_sessions_user
  ON web_chat_sessions (user_id, updated_at DESC)
  WHERE user_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_web_chat_references_source
  ON web_chat_references (source_type, source_id)
  WHERE source_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_web_tool_calls_session
  ON web_tool_calls (session_id, status, created_at DESC)
  WHERE session_id IS NOT NULL;

-- ============================================================================
-- Plugin schema
-- ============================================================================

-- Prometheus plugin database schema.
-- Depends on common_db.txt.
-- This keeps the plugin schema focused on conversation history, task logs,
-- file changes, sync state, and dashboard stats source data.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS plg_installations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  installation_id TEXT NOT NULL UNIQUE,
  host_name TEXT,
  os_name TEXT,
  os_version TEXT,
  os_arch TEXT,
  vscode_version TEXT,
  extension_version TEXT,
  last_seen_at TIMESTAMPTZ,
  payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS plg_workspace_bindings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  installation_id UUID REFERENCES plg_installations(id) ON DELETE SET NULL,
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  workspace_id UUID REFERENCES workspaces(id) ON DELETE SET NULL,
  repository_id UUID REFERENCES repositories(id) ON DELETE SET NULL,
  workspace_path TEXT NOT NULL,
  normalized_workspace_path TEXT NOT NULL,
  workspace_name TEXT,
  repository_url TEXT,
  repository_provider TEXT,
  branch_name TEXT,
  host_name TEXT,
  os_name TEXT,
  last_task_id TEXT,
  last_active_at TIMESTAMPTZ,
  payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (installation_id, normalized_workspace_path)
);

CREATE TABLE IF NOT EXISTS plg_tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id TEXT NOT NULL,
  ulid TEXT,
  source TEXT NOT NULL DEFAULT 'cline-fork',
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  installation_id UUID REFERENCES plg_installations(id) ON DELETE SET NULL,
  workspace_id UUID REFERENCES workspaces(id) ON DELETE SET NULL,
  workspace_binding_id UUID REFERENCES plg_workspace_bindings(id) ON DELETE SET NULL,
  repository_id UUID REFERENCES repositories(id) ON DELETE SET NULL,
  workspace_path TEXT,
  normalized_workspace_path TEXT,
  cwd_on_task_initialization TEXT,
  title TEXT NOT NULL,
  task TEXT,
  status TEXT NOT NULL DEFAULT 'completed'
    CHECK (status IN ('running', 'completed', 'failed', 'cancelled', 'unknown')),
  mode TEXT,
  model_id TEXT,
  shadow_git_config_work_tree TEXT,
  checkpoint_manager_error_message TEXT,
  conversation_history_deleted_range JSONB,
  is_favorited BOOLEAN NOT NULL DEFAULT false,
  source_started_at TIMESTAMPTZ,
  source_updated_at TIMESTAMPTZ,
  last_synced_at TIMESTAMPTZ,
  source_payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (installation_id, task_id)
);

CREATE TABLE IF NOT EXISTS plg_ui_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  plg_task_id UUID NOT NULL REFERENCES plg_tasks(id) ON DELETE CASCADE,
  seq INT NOT NULL,
  source_ts BIGINT,
  occurred_at TIMESTAMPTZ,
  message_type TEXT NOT NULL,
  ask_type TEXT,
  say_type TEXT,
  text TEXT,
  reasoning TEXT,
  images JSONB,
  files JSONB,
  partial BOOLEAN NOT NULL DEFAULT false,
  command_completed BOOLEAN,
  conversation_history_index INT,
  last_checkpoint_hash TEXT,
  is_checkpoint_checked_out BOOLEAN,
  is_operation_outside_workspace BOOLEAN,
  model_info JSONB,
  raw_message JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (plg_task_id, seq)
);

CREATE TABLE IF NOT EXISTS plg_api_conversation_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  plg_task_id UUID NOT NULL REFERENCES plg_tasks(id) ON DELETE CASCADE,
  seq INT NOT NULL,
  provider_message_id TEXT,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool', 'unknown')),
  content JSONB,
  model_info JSONB,
  metrics JSONB,
  source_ts BIGINT,
  occurred_at TIMESTAMPTZ,
  raw_message JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (plg_task_id, seq)
);

CREATE TABLE IF NOT EXISTS plg_task_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  plg_task_id UUID NOT NULL REFERENCES plg_tasks(id) ON DELETE CASCADE,
  seq INT NOT NULL,
  source TEXT NOT NULL DEFAULT 'ui_message',
  event_family TEXT NOT NULL
    CHECK (event_family IN ('message', 'tool', 'command', 'file', 'browser', 'mcp', 'checkpoint', 'error', 'system')),
  event_type TEXT NOT NULL,
  status TEXT
    CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled', 'unknown')),
  title TEXT,
  text TEXT,
  reasoning TEXT,
  tool_name TEXT,
  command TEXT,
  exit_code INT,
  payload JSONB,
  occurred_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (plg_task_id, seq)
);

CREATE TABLE IF NOT EXISTS plg_task_file_changes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  plg_task_id UUID NOT NULL REFERENCES plg_tasks(id) ON DELETE CASCADE,
  event_id UUID REFERENCES plg_task_events(id) ON DELETE SET NULL,
  file_path TEXT NOT NULL,
  change_type TEXT NOT NULL
    CHECK (change_type IN ('read', 'create', 'update', 'delete', 'rename', 'unknown')),
  diff TEXT,
  content_preview TEXT,
  read_line_start INT,
  read_line_end INT,
  operation_is_located_in_workspace BOOLEAN,
  raw_payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS plg_task_stats (
  plg_task_id UUID PRIMARY KEY REFERENCES plg_tasks(id) ON DELETE CASCADE,
  total_ui_messages INT NOT NULL DEFAULT 0,
  total_api_messages INT NOT NULL DEFAULT 0,
  tool_calls INT NOT NULL DEFAULT 0,
  file_reads INT NOT NULL DEFAULT 0,
  file_edits INT NOT NULL DEFAULT 0,
  file_creates INT NOT NULL DEFAULT 0,
  file_deletes INT NOT NULL DEFAULT 0,
  command_runs INT NOT NULL DEFAULT 0,
  browser_actions INT NOT NULL DEFAULT 0,
  mcp_calls INT NOT NULL DEFAULT 0,
  error_count INT NOT NULL DEFAULT 0,
  tokens_in BIGINT NOT NULL DEFAULT 0,
  tokens_out BIGINT NOT NULL DEFAULT 0,
  total_cost NUMERIC(12, 6) NOT NULL DEFAULT 0,
  first_event_at TIMESTAMPTZ,
  last_event_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS plg_raw_files (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  plg_task_id UUID REFERENCES plg_tasks(id) ON DELETE CASCADE,
  file_kind TEXT NOT NULL
    CHECK (file_kind IN ('task_history', 'ui_messages', 'api_conversation_history', 'task_metadata', 'other')),
  file_name TEXT NOT NULL,
  checksum TEXT NOT NULL,
  content JSONB NOT NULL,
  synced_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (plg_task_id, file_kind, file_name)
);

CREATE TABLE IF NOT EXISTS plg_sync_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  installation_id UUID REFERENCES plg_installations(id) ON DELETE SET NULL,
  workspace_binding_id UUID REFERENCES plg_workspace_bindings(id) ON DELETE SET NULL,
  sync_source TEXT NOT NULL DEFAULT 'bridge',
  status TEXT NOT NULL DEFAULT 'running'
    CHECK (status IN ('running', 'completed', 'failed', 'cancelled')),
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at TIMESTAMPTZ,
  scanned_tasks INT NOT NULL DEFAULT 0,
  inserted_tasks INT NOT NULL DEFAULT 0,
  updated_tasks INT NOT NULL DEFAULT 0,
  failed_tasks INT NOT NULL DEFAULT 0,
  error_message TEXT,
  payload JSONB
);

CREATE INDEX IF NOT EXISTS idx_plg_installations_user
  ON plg_installations (user_id, last_seen_at DESC);

CREATE INDEX IF NOT EXISTS idx_plg_workspace_bindings_workspace
  ON plg_workspace_bindings (workspace_id, last_active_at DESC);

CREATE INDEX IF NOT EXISTS idx_plg_tasks_workspace
  ON plg_tasks (workspace_id, source_updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_plg_tasks_user
  ON plg_tasks (user_id, source_updated_at DESC);




CREATE INDEX IF NOT EXISTS idx_plg_file_changes_task
  ON plg_task_file_changes (plg_task_id, file_path);

CREATE INDEX IF NOT EXISTS idx_plg_sync_runs_status
  ON plg_sync_runs (status, started_at DESC);

-- Additional lookup indexes
CREATE INDEX IF NOT EXISTS idx_plg_workspace_bindings_user
  ON plg_workspace_bindings (user_id, last_active_at DESC);

CREATE INDEX IF NOT EXISTS idx_plg_workspace_bindings_repository
  ON plg_workspace_bindings (repository_id, last_active_at DESC)
  WHERE repository_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_plg_tasks_installation_updated
  ON plg_tasks (installation_id, source_updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_plg_tasks_repository_updated
  ON plg_tasks (repository_id, source_updated_at DESC)
  WHERE repository_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_plg_tasks_status_updated
  ON plg_tasks (status, source_updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_plg_ui_messages_type
  ON plg_ui_messages (plg_task_id, message_type, seq);

CREATE INDEX IF NOT EXISTS idx_plg_task_events_family_status
  ON plg_task_events (plg_task_id, event_family, status, seq);

CREATE INDEX IF NOT EXISTS idx_plg_file_changes_path
  ON plg_task_file_changes (file_path);

CREATE INDEX IF NOT EXISTS idx_plg_sync_runs_installation
  ON plg_sync_runs (installation_id, started_at DESC)
  WHERE installation_id IS NOT NULL;

-- Additional plugin relation lookup indexes
CREATE INDEX IF NOT EXISTS idx_plg_tasks_workspace_binding
  ON plg_tasks (workspace_binding_id, source_updated_at DESC)
  WHERE workspace_binding_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_plg_file_changes_event
  ON plg_task_file_changes (event_id)
  WHERE event_id IS NOT NULL;


CREATE INDEX IF NOT EXISTS idx_plg_sync_runs_workspace_binding
  ON plg_sync_runs (workspace_binding_id, started_at DESC)
  WHERE workspace_binding_id IS NOT NULL;

