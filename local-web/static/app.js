const stageNames = {
  part1: "文献收集",
  part2: "Research Wiki",
  part3: "论证树",
  part4: "论文大纲",
  part5: "写作与修订",
  part6: "最终整理"
};

const stageActions = {
  part1: [
    ["part1-intake", "生成 intake 请求", "secondary"],
    ["confirm-intake", "确认并运行 Part 1", "warn"],
    ["part1-runner", "运行检索流程", ""],
    ["part1-export-table", "导出论文表", "secondary"]
  ],
  part2: [
    ["part2-generate", "生成 Wiki", ""],
    ["part2-health", "Wiki health", "secondary"]
  ],
  part3: [
    ["part3-seed-map", "生成 seed map", ""],
    ["part3-generate", "生成候选", ""],
    ["part3-compare", "生成比较", ""],
    ["part3-refine", "细化候选", "secondary"],
    ["part3-review", "查看选择表", "secondary"],
    ["part3-select", "锁定选择", "warn"]
  ],
  part4: [
    ["part4-generate", "生成大纲", ""],
    ["part4-check", "检查大纲", "secondary"]
  ],
  part5: [
    ["part5-prep", "Prep", ""],
    ["part5-draft", "Draft", ""],
    ["part5-review", "Review", ""],
    ["part5-revise", "Revise", ""],
    ["part5-all", "运行 Part 5 MVP", "warn"],
    ["part5-check", "检查 Part 5", "secondary"]
  ],
  part6: [
    ["part6-precheck", "只读预检", "secondary"],
    ["part6-authorize", "授权 Part 6", "warn"],
    ["part6-finalize", "运行 finalizer", "danger"],
    ["part6-check", "检查 package", "secondary"],
    ["part6-confirm-final", "确认最终决策", "danger"]
  ]
};

const appState = {
  data: null,
  contextId: null,
  selectedStage: "part1",
  jobs: new Map(),
  initialized: false,
  intakeDirty: false,
  fetching: false
};

const $ = (selector) => document.querySelector(selector);
const AUTO_REFRESH_MS = 3000;

function statusClass(stage) {
  if (!stage) return "";
  if (stage.status === "completed" && stage.gate_passed) return "completed";
  if (stage.status === "in_progress") return "in-progress";
  if (stage.status === "failed") return "failed";
  return "";
}

function gateBadge(stage) {
  if (!stage) return `<span class="badge wait">未知</span>`;
  if (stage.gate_passed) return `<span class="badge ok">gate passed</span>`;
  if (stage.status === "failed") return `<span class="badge fail">failed</span>`;
  return `<span class="badge wait">${stage.status || "not_started"}</span>`;
}

function artifactIcon(artifact) {
  if (!artifact.exists) return "x";
  if (artifact.schema_valid === false) return "!";
  return "✓";
}

function stageDescription(stageId) {
  const stages = appState.data?.manifest?.stages || [];
  const found = stages.find((stage) => stage.id === stageId);
  return found?.description || "";
}

async function fetchStatus(options = {}) {
  if (appState.fetching) return;
  appState.fetching = true;
  $("#liveStatus").textContent = "实时更新：同步中";
  const contextPart = appState.contextId ? `?context_id=${encodeURIComponent(appState.contextId)}` : "";
  try {
    const response = await fetch(`/api/status${contextPart}`);
    if (!response.ok) throw new Error(await response.text());
    appState.data = await response.json();
    if (!appState.contextId) {
      appState.contextId = appState.data.default_context_id || "root";
    }
    if (!appState.initialized && appState.data?.status?.current_stage) {
      appState.selectedStage = appState.data.status.current_stage;
    }
    appState.initialized = true;
    $("#liveStatus").textContent = "实时更新：开启";
    $("#lastUpdated").textContent = new Date().toLocaleTimeString("zh-CN", { hour12: false });
    render();
  } catch (error) {
    $("#liveStatus").textContent = "实时更新：中断";
    if (!options.silent) throw error;
  } finally {
    appState.fetching = false;
  }
}

function renderContextSelect() {
  const select = $("#contextSelect");
  select.innerHTML = "";
  for (const context of appState.data.contexts || []) {
    const option = document.createElement("option");
    option.value = context.id;
    option.textContent = context.is_latest ? `${context.label}（latest）` : context.label;
    select.append(option);
  }
  select.value = appState.contextId || appState.data.default_context_id || "root";
}

function renderOverview() {
  const status = appState.data.status;
  const summary = appState.data.summary || {};
  $("#activePath").textContent = appState.data.active_context?.path || "";
  $("#sourceCount").textContent = String(summary.source_count ?? 0);
  $("#wikiPages").textContent = String(summary.wiki_pages ?? 0);
  $("#readinessVerdict").textContent = summary.part5_readiness || "-";

  if (appState.data.status_error) {
    $("#nextActionTitle").textContent = "状态读取失败";
    $("#nextActionReason").textContent = appState.data.status_error.message;
    return;
  }

  const next = status?.next_action || {};
  $("#nextActionTitle").textContent = next.command || "当前没有可执行建议";
  $("#nextActionReason").textContent = next.reason || "所有可读状态已刷新。";
}

function arrayToLines(value) {
  if (!Array.isArray(value)) return "";
  return value.filter(Boolean).join("\n");
}

function linesToArray(value) {
  return String(value || "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

function setInputValue(id, value) {
  const element = $(id);
  if (element) element.value = value ?? "";
}

function intakeSource() {
  return appState.data?.part1_intake?.current || appState.data?.part1_intake?.template || {};
}

function renderIntakeForm(force = false) {
  if (!force && appState.intakeDirty) return;
  const intake = intakeSource();
  const timeRange = intake.time_range || {};
  const sourcePreference = intake.source_preference || {};
  setInputValue("#intakeId", intake.intake_id || "");
  setInputValue("#researchTopic", intake.research_topic || "");
  setInputValue("#researchQuestion", intake.research_question || "");
  setInputValue("#coreQuestions", arrayToLines(intake.core_research_questions));
  setInputValue("#disciplineFields", arrayToLines(intake.discipline_fields));
  setInputValue("#startYear", timeRange.start_year || 2015);
  setInputValue("#endYear", timeRange.end_year || new Date().getFullYear());
  setInputValue("#keywordsRequired", arrayToLines(intake.keywords_required));
  setInputValue("#keywordsSuggested", arrayToLines(intake.keywords_suggested));
  setInputValue("#documentTypes", arrayToLines(sourcePreference.document_types));
  setInputValue("#exclusions", arrayToLines(intake.exclusions || intake.exclusion_rules));
  setInputValue("#scopeNotes", intake.scope_notes || "");
  appState.intakeDirty = false;
  $("#intakeStatus").textContent = "Intake 表单已载入。";
}

function intakePayload() {
  return {
    intake_id: $("#intakeId").value.trim(),
    research_topic: $("#researchTopic").value.trim(),
    research_question: $("#researchQuestion").value.trim(),
    core_research_questions: linesToArray($("#coreQuestions").value),
    discipline_fields: linesToArray($("#disciplineFields").value),
    time_range: {
      start_year: Number($("#startYear").value || 2015),
      end_year: Number($("#endYear").value || new Date().getFullYear())
    },
    keywords_required: linesToArray($("#keywordsRequired").value),
    keywords_suggested: linesToArray($("#keywordsSuggested").value),
    exclusions: linesToArray($("#exclusions").value),
    source_preference: {
      priority_sources: ["cnki", "wanfang", "vip"],
      document_types: linesToArray($("#documentTypes").value),
      priority: "CNKI first"
    },
    scope_notes: $("#scopeNotes").value.trim()
  };
}

function renderStages() {
  const board = $("#stageBoard");
  const statuses = appState.data.status?.stages || {};
  board.innerHTML = "";

  Object.keys(stageNames).forEach((stageId) => {
    const stage = statuses[stageId] || {};
    const card = document.createElement("article");
    card.className = `stage-card ${statusClass(stage)} ${appState.selectedStage === stageId ? "active" : ""}`;
    card.tabIndex = 0;
    card.addEventListener("click", () => {
      appState.selectedStage = stageId;
      render();
    });
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        appState.selectedStage = stageId;
        render();
      }
    });

    const artifacts = (stage.artifacts || []).map((artifact) => {
      const linkClass = artifact.exists ? "artifact-link exists" : "artifact-link";
      const click = artifact.exists ? `data-artifact="${artifact.path}"` : "";
      const schema = artifact.schema_valid === true ? " · schema ok" : artifact.schema_valid === false ? " · schema fail" : "";
      return `
        <li class="artifact-item">
          <span>${artifactIcon(artifact)}</span>
          <a class="${linkClass}" href="#" ${click}>${artifact.path}${schema}</a>
        </li>
      `;
    }).join("");

    const pending = stage.pending_human_gates || [];
    const completed = stage.human_gates_completed || [];
    const gateText = [
      ...pending.map((gate) => `待确认：${gate}`),
      ...completed.map((gate) => `已确认：${gate}`)
    ].join(" / ");

    card.innerHTML = `
      <div class="stage-topline">
        <span class="stage-id">${stageId.toUpperCase()}</span>
        ${gateBadge(stage)}
      </div>
      <h3>${stageNames[stageId]}</h3>
      <p class="muted">${stageDescription(stageId)}</p>
      <ul class="artifact-list">${artifacts}</ul>
      ${gateText ? `<p class="gate-line">${gateText}</p>` : ""}
    `;
    board.append(card);
  });

  board.querySelectorAll("[data-artifact]").forEach((element) => {
    element.addEventListener("click", (event) => {
      event.preventDefault();
      openArtifact(event.currentTarget.getAttribute("data-artifact"));
    });
  });
}

function actionParams(actionId) {
  const params = {
    stage: appState.selectedStage,
    force: $("#forceInput").checked
  };

  if (["confirm-intake", "part6-authorize", "part6-confirm-final"].includes(actionId)) {
    params.notes = $("#notesInput").value.trim();
  }
  if (actionId === "part3-select") {
    params.notes = $("#notesInput").value.trim();
    params.candidate_id = $("#candidateInput").value.trim();
    params.candidate_source = $("#candidateSource").value;
  }
  if (actionId === "part6-finalize") {
    params.step = $("#part6Step").value;
  }
  return params;
}

function stageStatus(stageId) {
  return appState.data?.status?.stages?.[stageId] || {};
}

function stageComplete(stageId) {
  const stage = stageStatus(stageId);
  return stage.status === "completed" && stage.gate_passed === true;
}

function hasArtifact(stageId, path) {
  return Boolean((stageStatus(stageId).artifacts || []).some((artifact) => artifact.path === path && artifact.exists));
}

function pendingGate(stageId, gateId) {
  return (stageStatus(stageId).pending_human_gates || []).includes(gateId);
}

function currentContextIsWorkspace() {
  return /^ws_\d{3}$/.test(appState.contextId || "");
}

function hasPart3Candidates() {
  return (appState.data?.part3?.candidates || []).length >= 3;
}

function visibleStageActions(stageId) {
  const actions = [];

  if (stageId === "part1") {
    if (!stageComplete("part1") && currentContextIsWorkspace()) {
      actions.push(["part1-runner", "运行检索流程", ""]);
    }
    if (appState.data?.part1_references?.total || hasArtifact("part1", "raw-library/metadata.json")) {
      actions.push(["part1-export-table", "导出论文表", "secondary"]);
    }
    return actions;
  }

  if (stageId === "part2") {
    if (!stageComplete("part1") || stageComplete("part2")) return actions;
    if (!hasArtifact("part2", "research-wiki/index.json")) {
      actions.push(["part2-generate", "生成 Wiki", ""]);
      return actions;
    }
    actions.push(["part2-health", "检查 Wiki", "secondary"]);
    return actions;
  }

  if (stageId === "part3") {
    if (!stageComplete("part2") || stageComplete("part3")) return actions;
    if (!appState.data?.part3?.seed_map_exists) {
      actions.push(["part3-seed-map", "生成 seed map", ""]);
      return actions;
    }
    if (!hasPart3Candidates()) {
      actions.push(["part3-generate", "生成候选", ""]);
      return actions;
    }
    if (!appState.data?.part3?.comparison_exists) {
      actions.push(["part3-compare", "生成比较", ""]);
      return actions;
    }
    if (pendingGate("part3", "argument_tree_selected")) {
      actions.push(["part3-refine", "细化候选", "secondary"]);
    }
    return actions;
  }

  if (stageId === "part4") {
    if (!stageComplete("part3") || stageComplete("part4")) return actions;
    if (!hasArtifact("part4", "outputs/part4/paper_outline.json")) {
      actions.push(["part4-generate", "生成大纲", ""]);
      return actions;
    }
    actions.push(["part4-check", "检查大纲", "secondary"]);
    return actions;
  }

  if (stageId === "part5") {
    if (!stageComplete("part4") || stageComplete("part5")) return actions;
    actions.push(["part5-all", "运行 Part 5 MVP", ""]);
    if (hasArtifact("part5", "outputs/part5/manuscript_v2.md")) {
      actions.push(["part5-check", "检查 Part 5", "secondary"]);
    }
    return actions;
  }

  if (stageId === "part6") {
    if (!stageComplete("part5") || stageComplete("part6")) return actions;
    if (pendingGate("part6", "part6_finalization_authorized")) {
      actions.push(["part6-precheck", "只读预检", "secondary"]);
      actions.push(["part6-authorize", "授权 Part 6", "warn"]);
      return actions;
    }
    if (!hasArtifact("part6", "outputs/part6/submission_package_manifest.json")) {
      actions.push(["part6-finalize", "运行 finalizer", ""]);
      return actions;
    }
    if (pendingGate("part6", "part6_final_decision_confirmed")) {
      actions.push(["part6-confirm-final", "确认最终决策", "warn"]);
      return actions;
    }
    actions.push(["part6-check", "检查 package", "secondary"]);
    return actions;
  }

  return actions;
}

function renderActions() {
  $("#selectedStageTitle").textContent = `${appState.selectedStage.toUpperCase()} 操作`;
  $("#part3Decision").classList.add("hidden");
  $("#part6Decision").classList.toggle("hidden", appState.selectedStage !== "part6");

  const actionPanel = $("#actionButtons");
  actionPanel.innerHTML = "";

  const visibleActions = visibleStageActions(appState.selectedStage);
  $("#forceLine").classList.toggle(
    "hidden",
    !visibleActions.some(([id]) => ["part2-generate", "part3-refine", "part4-generate"].includes(id))
  );

  if (!visibleActions.length) {
    actionPanel.innerHTML = `<p class="empty-actions">当前阶段没有需要手动启动的动作。请看顶部“下一步”或对应的专用区域。</p>`;
    return;
  }

  for (const [id, label, tone] of visibleActions) {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.action = id;
    button.textContent = label;
    if (tone) button.className = tone;
    actionPanel.append(button);
  }

  actionPanel.querySelectorAll("[data-action]").forEach((button) => {
    button.addEventListener("click", () => runAction(button.dataset.action));
  });
}

function readableStrategy(strategy) {
  const labels = {
    case_application: "从案例进入，再总结可用方法",
    problem_solution: "先提出问题，再给出解决路径",
    theory_first: "先建立概念框架，再展开应用"
  };
  return labels[strategy] || strategy || "";
}

function cleanArgumentText(text) {
  return String(text || "")
    .replaceAll("Part 2 Evidence Synthesis、", "")
    .replaceAll("Part 2 Evidence Synthesis", "已有资料综合")
    .replaceAll("Source Evidence Digest:", "资料摘要：")
    .replaceAll("Part 2 Research Synthesis", "研究综合判断")
    .replaceAll("跨来源研究锚点", "研究重点")
    .replaceAll("wiki 页面", "资料页面")
    .replaceAll("登记 source_id", "已登记来源")
    .replaceAll("source_id", "来源")
    .replaceAll("Seed map 侧重：", "")
    .replace(/\s+/g, " ")
    .trim();
}

function readableThesis(candidate) {
  const topic = intakeSource().research_topic || "本研究";
  const strategy = candidate.strategy || "";
  if (strategy === "case_application") {
    return `这条路线先从具体案例和应用场景切入，再提炼可复制的方法，适合把“${topic}”写得更具体。`;
  }
  if (strategy === "problem_solution") {
    return `这条路线先说明当前教学和应用中的问题，再一步步提出解决路径，适合写成问题意识清晰的论文。`;
  }
  if (strategy === "theory_first") {
    return `这条路线先把核心概念和边界讲清楚，再讨论教学转化与应用方式，适合写成结构稳妥的论文。`;
  }
  return cleanArgumentText(candidate.thesis || "暂无 thesis");
}

function readableNode(node, index) {
  const raw = cleanArgumentText(node.claim || "");
  const nodeType = node.node_type || "";
  if (nodeType === "counterargument") {
    return `需要提醒自己：${raw.replace(/^反方限制[:：]\s*/, "")}`;
  }
  if (raw.length <= 96) {
    return raw;
  }
  const firstSentence = raw.split(/[。；;]/).find(Boolean) || raw;
  if (firstSentence.length <= 96) {
    return `${firstSentence}。`;
  }
  return `${firstSentence.slice(0, 92)}...`;
}

function renderPart3Candidates() {
  const target = $("#candidateOptions");
  const part3 = appState.data?.part3 || {};
  const candidates = part3.candidates || [];
  const recommendedId = part3.recommendation?.recommended_candidate_id;
  const selectedId = part3.selection?.selected_candidate_id;

  if (!candidates.length) {
    target.innerHTML = `
      <p class="muted">还没有候选论证树。先运行 Part 3 的 seed map、generate、compare。</p>
    `;
    return;
  }

  target.innerHTML = candidates.map((candidate) => {
    const candidateId = candidate.candidate_id || "";
    const isRecommended = candidateId === recommendedId;
    const isSelected = candidateId === selectedId;
    const score = typeof candidate.score === "number" ? candidate.score.toFixed(3) : "-";
    const nodes = Array.isArray(candidate.argument_nodes) ? candidate.argument_nodes.slice(0, 8) : [];
    const nodeHtml = nodes.map((node, index) => `
      <article class="argument-node">
        <div class="argument-node-id">${escapeHtml(node.node_id || "")}</div>
        <p>${escapeHtml(readableNode(node, index))}</p>
      </article>
    `).join("");
    return `
      <article class="candidate-card ${isRecommended ? "recommended" : ""}">
        <div class="candidate-head">
          <div>
            <div class="candidate-id">${escapeHtml(candidateId)}</div>
            <p class="muted">${escapeHtml(readableStrategy(candidate.strategy))} · score ${score}</p>
          </div>
          <div>
            ${isRecommended ? '<span class="badge ok">推荐</span>' : ""}
            ${isSelected ? '<span class="badge wait">已选择</span>' : ""}
          </div>
        </div>
        <p class="candidate-thesis">${escapeHtml(readableThesis(candidate))}</p>
        ${nodeHtml ? `<div class="node-list"><h3>论点结构</h3>${nodeHtml}</div>` : ""}
        <div class="candidate-actions">
          <button type="button" data-candidate-id="${escapeHtml(candidateId)}">选择这个论证树</button>
        </div>
      </article>
    `;
  }).join("");

  target.querySelectorAll("[data-candidate-id]").forEach((button) => {
    button.addEventListener("click", () => chooseCandidate(button.dataset.candidateId));
  });
}

function renderMemory() {
  const memory = $("#memoryList");
  const items = appState.data.process_memory || [];
  if (!items.length) {
    memory.innerHTML = `<p class="muted">暂无 process-memory 记录。</p>`;
    return;
  }
  memory.innerHTML = items.map((item) => {
    const data = item.data || {};
    const event = data.event || item.file;
    const timestamp = data.timestamp || data.confirmed_at || data.failed_at || "";
    return `
      <div class="memory-item">
        <strong>${event}</strong>
        <p class="muted">${timestamp}</p>
        <code>${item.file}</code>
      </div>
    `;
  }).join("");
}

function renderReferences() {
  const list = $("#referenceList");
  const meta = $("#referenceMeta");
  const snapshot = appState.data?.part1_references || {};
  const references = snapshot.references || [];
  meta.textContent = references.length ? `${snapshot.total || references.length} 个下载文件，${snapshot.accepted_count || 0} 个 accepted` : "";
  if (!references.length) {
    list.innerHTML = `<p class="muted">当前上下文还没有 Part 1 下载文件。</p>`;
    return;
  }
  list.innerHTML = references.map((item) => {
    const status = [item.library_status, item.relevance_tier, item.relevance_score].filter(Boolean).join(" · ");
    const bibliographic = [item.authors, item.year, item.journal].filter(Boolean).join(" · ");
    return `
      <article class="reference-item">
        <span class="reference-file">${escapeHtml(item.file_name || item.source_id || "")}</span>
        <p class="reference-title">${escapeHtml(item.title || "未记录题名")}</p>
        <p class="muted">${escapeHtml(bibliographic || item.local_path || "")}</p>
        <div class="reference-tags">
          ${item.source_name ? `<span>${escapeHtml(item.source_name)}</span>` : ""}
          ${item.query_id ? `<span>${escapeHtml(item.query_id)}</span>` : ""}
          ${status ? `<span>${escapeHtml(status)}</span>` : ""}
          ${item.local_exists ? "<span>PDF exists</span>" : "<span>PDF missing</span>"}
        </div>
      </article>
    `;
  }).join("");
}

function renderJobStatusHint(job) {
  const statusText = `${job.action_id}: ${job.status}`;
  if (job.status === "failed") {
    $("#artifactPreview").textContent = `${statusText}\n${job.error || "动作失败。需要时可在终端查看服务日志 /tmp/research-local-web.log。"}`;
    return;
  }
  $("#artifactPreview").textContent = statusText;
}

function render() {
  renderContextSelect();
  renderOverview();
  renderStages();
  renderActions();
  renderIntakeForm();
  renderPart3Candidates();
  renderReferences();
  renderMemory();
}

async function runAction(actionId) {
  const params = actionParams(actionId);
  if (["confirm-intake", "part3-select", "part6-authorize", "part6-confirm-final"].includes(actionId) && !params.notes) {
    $("#artifactPreview").textContent = "这个动作需要先填写决策备注。";
    return;
  }
  if (actionId === "part3-select" && !params.candidate_id) {
    $("#artifactPreview").textContent = "锁定论证树前，需要填写候选 ID。";
    return;
  }

  const response = await fetch("/api/actions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      context_id: appState.contextId,
      action_id: actionId,
      params
    })
  });
  const payload = await response.json();
  if (!response.ok) {
    $("#artifactPreview").textContent = payload.error || "动作启动失败。";
    return;
  }
  appState.jobs.set(payload.job_id, payload);
  renderJobStatusHint(payload);
  pollJob(payload.job_id);
}

async function submitIntake(runAfterSave) {
  const notes = $("#notesInput").value.trim();
  if (runAfterSave && !notes) {
    $("#intakeStatus").textContent = "保存并运行前，请先填写右侧“决策备注”。";
    return;
  }
  const actionId = runAfterSave ? "save-intake-run" : "save-intake";
  const response = await fetch("/api/actions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      context_id: "root",
      action_id: actionId,
      params: {
        intake: intakePayload(),
        notes
      }
    })
  });
  const payload = await response.json();
  if (!response.ok) {
    $("#intakeStatus").textContent = payload.error || "Intake 保存失败。";
    return;
  }
  appState.intakeDirty = false;
  appState.jobs.set(payload.job_id, payload);
  $("#intakeStatus").textContent = runAfterSave ? "已启动：保存、确认 intake、创建 workspace、运行 Part 1。" : "已启动：保存 intake。";
  renderJobStatusHint(payload);
  pollJob(payload.job_id);
}

function chooseCandidate(candidateId) {
  appState.selectedStage = "part3";
  $("#candidateInput").value = candidateId;
  $("#candidateSource").value = "original";
  if (!$("#notesInput").value.trim()) {
    $("#notesInput").value = `网页人工选择：${candidateId}`;
  }
  runAction("part3-select");
}

async function pollJob(jobId) {
  const response = await fetch(`/api/jobs/${jobId}`);
  const job = await response.json();
  appState.jobs.set(jobId, job);
  renderJobStatusHint(job);
  if (["queued", "running"].includes(job.status)) {
    window.setTimeout(() => pollJob(jobId), 1200);
    return;
  }
  await fetchStatus();
}

async function openArtifact(path) {
  const response = await fetch(`/api/artifact?context_id=${encodeURIComponent(appState.contextId)}&path=${encodeURIComponent(path)}`);
  const payload = await response.json();
  if (!response.ok) {
    $("#artifactPreview").textContent = payload.error || "无法读取文件。";
    return;
  }
  $("#artifactMeta").textContent = `${payload.path} · ${payload.size} bytes${payload.truncated ? " · 已截断" : ""}`;
  $("#artifactPreview").textContent = payload.content;
}

function escapeHtml(text) {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

$("#contextSelect").addEventListener("change", async (event) => {
  appState.contextId = event.target.value;
  await fetchStatus();
});

$("#refreshButton").addEventListener("click", fetchStatus);
$("#saveIntakeButton").addEventListener("click", () => submitIntake(false));
$("#runIntakeButton").addEventListener("click", () => submitIntake(true));
$("#reloadIntakeButton").addEventListener("click", () => {
  appState.intakeDirty = false;
  renderIntakeForm(true);
});

$("#intakeForm").querySelectorAll("input, textarea").forEach((element) => {
  element.addEventListener("input", () => {
    appState.intakeDirty = true;
    $("#intakeStatus").textContent = "Intake 有未保存修改。";
  });
});

fetchStatus().catch((error) => {
  $("#nextActionTitle").textContent = "启动失败";
  $("#nextActionReason").textContent = error.message;
});

window.setInterval(() => {
  fetchStatus({ silent: true });
}, AUTO_REFRESH_MS);
