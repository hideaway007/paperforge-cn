const stageNames = {
  part1: "文献收集",
  part2: "研究 Wiki",
  part3: "论证树",
  part4: "论文大纲",
  part5: "写作与修订",
  part6: "最终整理"
};

const stageIndexLabels = {
  part1: "阶段 1",
  part2: "阶段 2",
  part3: "阶段 3",
  part4: "阶段 4",
  part5: "阶段 5",
  part6: "阶段 6"
};

const stageIcons = {
  part1: "upload_file",
  part2: "menu_book",
  part3: "psychology",
  part4: "format_list_bulleted",
  part5: "edit_note",
  part6: "verified"
};

const stageActions = {
  part1: [
    ["part1-intake", "生成研究信息请求", "secondary"],
    ["confirm-intake", "确认并运行阶段 1", "warn"],
    ["part1-runner", "运行检索流程", ""],
    ["part1-export-table", "导出论文表", "secondary"]
  ],
  part2: [
    ["part2-generate", "生成 Wiki", ""],
    ["part2-health", "检查 Wiki", "secondary"]
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
    ["part5-prep", "准备写作输入包", ""],
    ["part5-draft", "生成初稿", ""],
    ["part5-review", "生成审查报告", ""],
    ["part5-revise", "生成修订稿", ""],
    ["part5-all", "运行阶段 5 完整流程", "warn"],
    ["part5-check", "检查阶段 5", "secondary"]
  ],
  part6: [
    ["part6-precheck", "只读预检", "secondary"],
    ["part6-authorize", "授权阶段 6", "warn"],
    ["part6-finalize", "运行最终整理", "danger"],
    ["part6-check", "检查交付包", "secondary"],
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
  if (stage.gate_passed) return `<span class="badge ok">已通过</span>`;
  if (stage.status === "failed") return `<span class="badge fail">失败</span>`;
  const labels = {
    not_started: "未开始",
    in_progress: "运行中",
    completed: "已完成"
  };
  return `<span class="badge wait">${labels[stage.status] || stage.status || "未开始"}</span>`;
}

function artifactIcon(artifact) {
  if (!artifact.exists) return "x";
  if (artifact.schema_valid === false) return "!";
  return "✓";
}

function setText(selector, value) {
  const element = $(selector);
  if (element) element.textContent = value;
}

function allStageArtifacts() {
  const stages = appState.data?.status?.stages || {};
  return Object.keys(stageNames).flatMap((stageId) =>
    (stages[stageId]?.artifacts || []).map((artifact) => ({ ...artifact, stageId }))
  );
}

function artifactLabel(path) {
  const labels = {
    "raw-library/metadata.json": "文献库元数据",
    "outputs/part1/authenticity_report.json": "真实性报告",
    "research-wiki/index.json": "研究 Wiki 索引",
    "outputs/part3/argument_tree.json": "权威论证树",
    "outputs/part4/paper_outline.json": "论文大纲",
    "outputs/part5/manuscript_v2.md": "阶段 5 修订稿",
    "outputs/part5/review_matrix.json": "审查矩阵",
    "outputs/part5/review_report.md": "审查报告",
    "outputs/part5/revision_log.json": "修订记录",
    "outputs/part5/part6_readiness_decision.json": "阶段 6 交接判断",
    "outputs/part6/final_manuscript.md": "最终稿",
    "outputs/part6/claim_risk_report.json": "论断风险审计",
    "outputs/part6/citation_consistency_report.json": "引用一致性审计",
    "outputs/part6/submission_package_manifest.json": "交付包清单",
    "outputs/part6/final_readiness_decision.json": "最终就绪判断"
  };
  return labels[path] || path.split("/").pop() || path;
}

function artifactStatusText(artifact) {
  if (!artifact?.exists) return "未生成";
  if (artifact.schema_valid === false) return "结构错误";
  if (artifact.schema_valid === true) return "结构有效";
  return "已存在";
}

function readableCommand(command) {
  const labels = {
    "part1-intake": "生成研究信息请求",
    "confirm-intake": "确认研究信息并运行阶段 1",
    "part1-runner": "运行阶段 1 检索流程",
    "part1-export-table": "导出已下载论文表",
    "part2-generate": "生成研究 Wiki",
    "part2-health": "检查 Wiki 健康状态",
    "part3-seed-map": "生成论证 seed map",
    "part3-generate": "生成候选论证树",
    "part3-compare": "生成候选比较",
    "part3-refine": "细化候选论证树",
    "part3-select": "锁定论证树选择",
    "part4-generate": "生成论文大纲",
    "part4-check": "检查论文大纲",
    "part5-all": "运行阶段 5 完整流程",
    "part5-check": "检查阶段 5",
    "part6-precheck": "阶段 6 只读预检",
    "part6-authorize": "授权阶段 6",
    "part6-finalize": "运行最终整理",
    "part6-check": "检查交付包",
    "part6-confirm-final": "确认最终决策",
    "save-intake": "保存研究信息",
    "save-intake-run": "保存研究信息并运行阶段 1"
  };
  return labels[command] || command;
}

function stageDescription(stageId) {
  const descriptions = {
    part1: "文献检索、下载、真实性校验与资料库构建",
    part2: "把资料库转成研究 Wiki，维护证据映射与冲突记录",
    part3: "生成三份候选论证树，比较后由用户锁定",
    part4: "生成大纲三件套，并校验与论证树对齐",
    part5: "生成正文、审查报告、修订稿与阶段 6 交接判断",
    part6: "用户授权后生成最终稿、审计和交付包清单"
  };
  return descriptions[stageId] || "";
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
    option.textContent = context.is_latest ? `${context.label}（最新）` : context.label;
    select.append(option);
  }
  select.value = appState.contextId || appState.data.default_context_id || "root";
}

function renderOverview() {
  const status = appState.data.status;
  const summary = appState.data.summary || {};
  const stages = status?.stages || {};
  const stageIds = Object.keys(stageNames);
  const completedCount = stageIds.filter((stageId) => {
    const stage = stages[stageId] || {};
    return stage.status === "completed" && stage.gate_passed === true;
  }).length;
  const progress = Math.round((completedCount / stageIds.length) * 100);
  const artifacts = allStageArtifacts();
  const existingArtifacts = artifacts.filter((artifact) => artifact.exists);
  const references = appState.data?.part1_references?.references || [];
  const acceptedCount = appState.data?.part1_references?.accepted_count ?? references.filter((item) => item.library_status === "accepted").length;
  const acceptedReferences = references.filter((item) => item.library_status === "accepted");
  const cnkiCount = acceptedReferences.filter((item) => {
    const text = `${item.source_name || ""} ${item.query_id || ""}`.toLowerCase();
    return text.includes("cnki") || text.includes("知网");
  }).length;
  const cnkiRatio = acceptedCount ? Math.round((cnkiCount / acceptedCount) * 100) : 0;
  const currentStage = status?.current_stage || appState.selectedStage || "part1";
  const contextId = appState.data.active_context?.id || appState.contextId || "root";
  const contextKind = contextId === "root" ? "root 控制面" : "隔离工作区";
  const authenticity = artifacts.find((artifact) => artifact.path === "outputs/part1/authenticity_report.json");
  const excludedCount = references.filter((item) => item.library_status === "excluded").length;

  setText("#activePath", appState.data.active_context?.path || "");
  setText("#sourceCount", String(summary.source_count ?? 0));
  setText("#wikiPages", String(summary.wiki_pages ?? 0));
  setText("#artifactCount", String(existingArtifacts.length));
  setText("#acceptedCount", `${acceptedCount} / 40`);
  setText("#cnkiRatio", `${cnkiRatio}%`);
  setText("#authenticityStatus", artifactStatusText(authenticity));
  setText("#excludedCount", String(excludedCount));
  setText("#readinessVerdict", summary.part5_readiness || "未形成");
  setText("#contextCrumb", contextId === "root" ? "root" : `root / ${contextId}`);
  setText("#contextKind", contextKind);
  setText("#currentStageLabel", `当前阶段：${stageNames[currentStage] || currentStage}`);
  setText("#stageProgress", `完成度：${completedCount}/${stageIds.length}`);
  setText("#progressPercent", `${progress}%`);
  setText("#workflowDigest", `${stageNames[currentStage] || "当前阶段"}正在作为主工作面；已存在 ${existingArtifacts.length} 个阶段产物，人工确认点仍以右侧决策中心为准。`);
  const progressFill = $("#progressFill");
  if (progressFill) progressFill.style.width = `${progress}%`;

  if (appState.data.status_error) {
    setText("#nextActionTitle", "状态读取失败");
    const message = appState.data.status_error.message || "";
    const readableError = message.includes("runtime/state.json")
      ? "缺少运行状态文件。请先在项目根目录执行初始化命令，再刷新本页面。"
      : `本地状态接口返回异常：${message}`;
    setText("#nextActionReason", readableError);
    return;
  }

  const next = status?.next_action || {};
  setText("#nextActionTitle", next.command ? readableCommand(next.command) : "当前没有可执行建议");
  setText("#nextActionReason", next.reason || "所有可读状态已刷新。");
}

function renderArtifactSummary() {
  const target = $("#artifactSummaryList");
  if (!target) return;
  const artifacts = allStageArtifacts()
    .filter((artifact) => artifact.exists)
    .slice(0, 6);
  if (!artifacts.length) {
    target.innerHTML = `<p class="muted">当前上下文还没有可核查的权威产物。</p>`;
    return;
  }
  target.innerHTML = artifacts.map((artifact) => `
    <button class="artifact-summary-item" type="button" data-artifact="${escapeHtml(artifact.path)}">
      <span class="material-symbols-outlined">${stageIcons[artifact.stageId] || "description"}</span>
      <span>
        <strong>${escapeHtml(artifactLabel(artifact.path))}</strong>
        <small>${escapeHtml(stageIndexLabels[artifact.stageId] || artifact.stageId)} · ${escapeHtml(artifactStatusText(artifact))}</small>
      </span>
    </button>
  `).join("");
  target.querySelectorAll("[data-artifact]").forEach((element) => {
    element.addEventListener("click", () => openArtifact(element.getAttribute("data-artifact")));
  });
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
  $("#intakeStatus").textContent = "研究信息表单已载入。";
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
      const schema = artifact.schema_valid === true ? " · 结构有效" : artifact.schema_valid === false ? " · 结构错误" : "";
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
        <span class="stage-id"><span class="material-symbols-outlined">${stageIcons[stageId]}</span>${stageIndexLabels[stageId]}</span>
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
      actions.push(["part3-select", "锁定选择", "warn"]);
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
    actions.push(["part5-all", "运行阶段 5 完整流程", ""]);
    if (hasArtifact("part5", "outputs/part5/manuscript_v2.md")) {
      actions.push(["part5-check", "检查阶段 5", "secondary"]);
    }
    return actions;
  }

  if (stageId === "part6") {
    if (!stageComplete("part5") || stageComplete("part6")) return actions;
    if (pendingGate("part6", "part6_finalization_authorized")) {
      actions.push(["part6-precheck", "只读预检", "secondary"]);
      actions.push(["part6-authorize", "授权阶段 6", "warn"]);
      return actions;
    }
    if (!hasArtifact("part6", "outputs/part6/submission_package_manifest.json")) {
      actions.push(["part6-finalize", "运行最终整理", ""]);
      return actions;
    }
    if (pendingGate("part6", "part6_final_decision_confirmed")) {
      actions.push(["part6-confirm-final", "确认最终决策", "warn"]);
      return actions;
    }
    actions.push(["part6-check", "检查交付包", "secondary"]);
    return actions;
  }

  return actions;
}

function renderActions() {
  $("#selectedStageTitle").textContent = `${stageIndexLabels[appState.selectedStage] || "当前阶段"} 操作`;
  $("#part3Decision").classList.toggle("hidden", appState.selectedStage !== "part3");
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

function readableReferenceToken(token) {
  const labels = {
    accepted: "已接受",
    excluded: "已排除",
    success: "已下载",
    failed: "失败",
    pending: "待处理"
  };
  return labels[token] || token;
}

function renderPart3Candidates() {
  const target = $("#candidateOptions");
  const part3 = appState.data?.part3 || {};
  const candidates = part3.candidates || [];
  const recommendedId = part3.recommendation?.recommended_candidate_id;
  const selectedId = part3.selection?.selected_candidate_id;

  if (!candidates.length) {
    target.innerHTML = `
      <p class="muted">还没有候选论证树。先运行阶段 3 的 seed map、候选生成与比较。</p>
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
            <p class="muted">${escapeHtml(readableStrategy(candidate.strategy))} · 得分 ${score}</p>
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
  meta.textContent = references.length ? `${snapshot.total || references.length} 个下载文件，${snapshot.accepted_count || 0} 个已接受来源` : "";
  if (!references.length) {
    list.innerHTML = `<p class="muted">当前上下文还没有阶段 1 下载文件。</p>`;
    return;
  }
  const rows = references.map((item) => {
    const status = [item.library_status, item.relevance_tier, item.relevance_score]
      .filter(Boolean)
      .map(readableReferenceToken)
      .join(" · ");
    const bibliographic = [item.authors, item.year, item.journal].filter(Boolean).join(" · ");
    return `
      <tr>
        <td>
          <strong>${escapeHtml(item.title || "未记录题名")}</strong>
          <small>${escapeHtml(item.file_name || item.source_id || "")}</small>
        </td>
        <td>${escapeHtml(item.source_name || "未记录")}</td>
        <td>${escapeHtml(bibliographic || "未记录")}</td>
        <td><span class="ledger-chip">${escapeHtml(status || item.download_status || "待处理")}</span></td>
        <td>${item.local_exists ? "已落地" : "缺失"}</td>
      </tr>
    `;
  }).join("");
  list.innerHTML = `
    <div class="source-ledger">
      <table>
        <thead>
          <tr>
            <th>题名与文件</th>
            <th>来源</th>
            <th>作者 / 年份 / 期刊</th>
            <th>状态</th>
            <th>本地文件</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
  `;
}

function renderPart6Readiness() {
  const stage = stageStatus("part6");
  const pending = stage.pending_human_gates || [];
  const completed = stage.human_gates_completed || [];
  const readiness = appState.data?.summary?.part5_readiness || "未形成";
  setText("#readinessVerdict", readiness);
  setText(
    "#readinessReason",
    readiness === "未形成"
      ? "阶段 5 尚未形成可交接判断，阶段 6 不应启动。"
      : "这是阶段 5 给出的交接判断，不等于最终提交许可。"
  );

  const gateList = $("#part6GateList");
  if (gateList) {
    const rows = [
      ["part6_finalization_authorized", "授权进入最终整理"],
      ["part6_final_decision_confirmed", "确认最终就绪判断与交付包"]
    ];
    gateList.innerHTML = rows.map(([gateId, label]) => {
      const done = completed.includes(gateId);
      const waiting = pending.includes(gateId);
      const text = done ? "已记录" : waiting ? "待人工确认" : "未到达";
      return `
        <div class="gate-check ${done ? "done" : waiting ? "waiting" : ""}">
          <span class="material-symbols-outlined">${done ? "check_circle" : "radio_button_unchecked"}</span>
        <strong>${label}</strong>
        <small>${text}</small>
        </div>
      `;
    }).join("");
  }

  const packageList = $("#part6ArtifactList");
  if (packageList) {
    const artifacts = (stage.artifacts || []).filter((artifact) => artifact.path?.startsWith("outputs/part6/"));
    if (!artifacts.length) {
      packageList.innerHTML = `<p class="muted">阶段 6 产物尚未生成。</p>`;
    } else {
      packageList.innerHTML = artifacts.map((artifact) => `
        <button type="button" class="package-item ${artifact.exists ? "exists" : ""}" ${artifact.exists ? `data-artifact="${escapeHtml(artifact.path)}"` : ""}>
          <span>${escapeHtml(artifactLabel(artifact.path))}</span>
          <small>${escapeHtml(artifactStatusText(artifact))}</small>
        </button>
      `).join("");
      packageList.querySelectorAll("[data-artifact]").forEach((element) => {
        element.addEventListener("click", () => openArtifact(element.getAttribute("data-artifact")));
      });
    }
  }

  const canAuthorize = stageComplete("part5") && pending.includes("part6_finalization_authorized");
  const canFinalize = stageComplete("part5") && !pending.includes("part6_finalization_authorized") && !stageComplete("part6");
  const canConfirm = pending.includes("part6_final_decision_confirmed");
  $("#authorizePart6Button").disabled = !canAuthorize;
  $("#runPart6Button").disabled = !canFinalize;
  $("#confirmPart6Button").disabled = !canConfirm;
}

function renderJobStatusHint(job) {
  const statusLabels = {
    queued: "排队中",
    running: "运行中",
    completed: "已完成",
    failed: "失败"
  };
  const statusText = `${readableCommand(job.action_id)}：${statusLabels[job.status] || job.status}`;
  if (job.status === "failed") {
    $("#artifactPreview").textContent = `${statusText}\n${job.error || "动作失败。需要时可在终端查看服务日志 /tmp/research-local-web.log。"}`;
    return;
  }
  $("#artifactPreview").textContent = statusText;
}

function render() {
  renderContextSelect();
  renderOverview();
  renderArtifactSummary();
  renderStages();
  renderActions();
  renderIntakeForm();
  renderPart3Candidates();
  renderPart6Readiness();
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
    $("#intakeStatus").textContent = payload.error || "研究信息保存失败。";
    return;
  }
  appState.intakeDirty = false;
  appState.jobs.set(payload.job_id, payload);
  $("#intakeStatus").textContent = runAfterSave ? "已启动：保存、确认研究信息、创建隔离工作区、运行阶段 1。" : "已启动：保存研究信息。";
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
  $("#artifactMeta").textContent = `${payload.path} · ${payload.size} 字节${payload.truncated ? " · 已截断" : ""}`;
  $("#artifactPreview").textContent = payload.content;
}

function escapeHtml(text) {
  return String(text ?? "")
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
$("#authorizePart6Button").addEventListener("click", () => runAction("part6-authorize"));
$("#runPart6Button").addEventListener("click", () => runAction("part6-finalize"));
$("#confirmPart6Button").addEventListener("click", () => runAction("part6-confirm-final"));
$("#reloadIntakeButton").addEventListener("click", () => {
  appState.intakeDirty = false;
  renderIntakeForm(true);
});

$("#intakeForm").querySelectorAll("input, textarea").forEach((element) => {
  element.addEventListener("input", () => {
    appState.intakeDirty = true;
    $("#intakeStatus").textContent = "研究信息有未保存修改。";
  });
});

fetchStatus().catch((error) => {
  $("#nextActionTitle").textContent = "启动失败";
  $("#nextActionReason").textContent = error.message;
});

window.setInterval(() => {
  fetchStatus({ silent: true });
}, AUTO_REFRESH_MS);
