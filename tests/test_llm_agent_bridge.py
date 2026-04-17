from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BRIDGE_PATH = PROJECT_ROOT / "runtime" / "llm_agent_bridge.py"
WRITER_BRIDGE_PATH = PROJECT_ROOT / "runtime" / "llm_writer_bridge.py"


def load_bridge():
    spec = importlib.util.spec_from_file_location("llm_agent_bridge", BRIDGE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_writer_bridge():
    spec = importlib.util.spec_from_file_location("llm_writer_bridge", WRITER_BRIDGE_PATH)
    module = importlib.util.module_from_spec(spec)
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class LLMAgentBridgeTest(unittest.TestCase):
    def setUp(self):
        self.bridge = load_bridge()
        self.tempdir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.tempdir.name)
        self.old_env = {
            "RTM_ARGUMENTAGENT_COMMAND": os.environ.get("RTM_ARGUMENTAGENT_COMMAND"),
            "RTM_ARGUMENTAGENT_TIMEOUT": os.environ.get("RTM_ARGUMENTAGENT_TIMEOUT"),
            "RTM_WRITEAGENT_COMMAND": os.environ.get("RTM_WRITEAGENT_COMMAND"),
            "RTM_WRITEAGENT_TIMEOUT": os.environ.get("RTM_WRITEAGENT_TIMEOUT"),
        }
        os.environ.pop("RTM_ARGUMENTAGENT_COMMAND", None)
        os.environ.pop("RTM_ARGUMENTAGENT_TIMEOUT", None)
        os.environ.pop("RTM_WRITEAGENT_COMMAND", None)
        os.environ.pop("RTM_WRITEAGENT_TIMEOUT", None)

    def tearDown(self):
        for key, value in self.old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tempdir.cleanup()

    def write_json(self, rel_path: str, payload: dict) -> None:
        path = self.project_root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)

    def read_json(self, rel_path: str) -> dict:
        with open(self.project_root / rel_path, encoding="utf-8") as f:
            return json.load(f)

    def test_request_returns_none_when_command_is_not_configured(self):
        result = self.bridge.request_llm_agent(
            self.project_root,
            agent_name="argumentagent",
            task="part3_compare_candidates",
            skill="part3-argument-compare",
            output_ref="outputs/part3/comparison.json",
            input_paths=[],
            instructions=["Compare candidate argument trees."],
        )

        self.assertIsNone(result)

    def test_request_runs_fake_command_and_reads_input_artifacts(self):
        self.write_json("outputs/part3/candidate.json", {"id": "candidate_a"})
        (self.project_root / "notes.md").write_text("human note", encoding="utf-8")
        fake_agent = self.project_root / "fake_argumentagent.py"
        fake_agent.write_text(
            (
                "import json, sys\n"
                "request = json.load(sys.stdin)\n"
                "assert request['agent_name'] == 'argumentagent'\n"
                "assert request['task'] == 'part3_compare_candidates'\n"
                "assert request['skill'] == 'part3-argument-compare'\n"
                "assert request['output_ref'] == 'outputs/part3/comparison.json'\n"
                "inputs = {item['path']: item for item in request['inputs']}\n"
                "assert inputs['outputs/part3/candidate.json']['kind'] == 'json'\n"
                "assert inputs['outputs/part3/candidate.json']['content']['id'] == 'candidate_a'\n"
                "assert inputs['notes.md']['kind'] == 'text'\n"
                "assert inputs['notes.md']['content'] == 'human note'\n"
                "assert inputs['missing.json']['exists'] is False\n"
                "assert 'Do not confirm or bypass human gates.' in request['hard_constraints']\n"
                "print(json.dumps({\n"
                "  'proposal': 'Choose candidate A because it has better source traceability.',\n"
                "  'artifacts': [{'path': 'outputs/part3/comparison.json'}]\n"
                "}, ensure_ascii=False))\n"
            ),
            encoding="utf-8",
        )
        os.environ["RTM_ARGUMENTAGENT_COMMAND"] = f"{sys.executable} {fake_agent}"
        os.environ["RTM_ARGUMENTAGENT_TIMEOUT"] = "5"

        result = self.bridge.request_llm_agent(
            self.project_root,
            agent_name="argumentagent",
            task="part3_compare_candidates",
            skill="part3-argument-compare",
            output_ref="outputs/part3/comparison.json",
            input_paths=["outputs/part3/candidate.json", "notes.md", "missing.json"],
            instructions=["Compare candidate argument trees."],
        )

        self.assertIsNotNone(result)
        self.assertEqual("argumentagent", result.agent_name)
        self.assertEqual(
            "Choose candidate A because it has better source traceability.",
            result.proposal,
        )
        self.assertEqual(
            [{"path": "outputs/part3/comparison.json"}],
            result.artifacts,
        )

    def test_request_rejects_non_json_output(self):
        fake_agent = self.project_root / "fake_bad_argumentagent.py"
        fake_agent.write_text("print('not json')\n", encoding="utf-8")
        os.environ["RTM_ARGUMENTAGENT_COMMAND"] = f"{sys.executable} {fake_agent}"

        with self.assertRaisesRegex(RuntimeError, "必须输出 JSON"):
            self.bridge.request_llm_agent(
                self.project_root,
                agent_name="argumentagent",
                task="part3_compare_candidates",
                skill="part3-argument-compare",
                output_ref="outputs/part3/comparison.json",
                input_paths=[],
                instructions=[],
            )

    def test_request_restores_and_rejects_protected_file_writes(self):
        self.write_json("runtime/state.json", {"status": "before"})
        fake_agent = self.project_root / "fake_mutating_argumentagent.py"
        fake_agent.write_text(
            (
                "import json, pathlib, sys\n"
                "request = json.load(sys.stdin)\n"
                "root = pathlib.Path(request['project_root'])\n"
                "(root / 'runtime' / 'state.json').write_text('{\"status\":\"mutated\"}', encoding='utf-8')\n"
                "(root / 'outputs' / 'part3').mkdir(parents=True, exist_ok=True)\n"
                "(root / 'outputs' / 'part3' / 'argument_tree.json').write_text('{\"bad\":true}', encoding='utf-8')\n"
                "(root / 'process-memory').mkdir(parents=True, exist_ok=True)\n"
                "(root / 'process-memory' / '20260417_bad_gate.json').write_text('{\"bad\":true}', encoding='utf-8')\n"
                "print(json.dumps({'proposal': 'done'}, ensure_ascii=False))\n"
            ),
            encoding="utf-8",
        )
        os.environ["RTM_ARGUMENTAGENT_COMMAND"] = f"{sys.executable} {fake_agent}"

        with self.assertRaisesRegex(RuntimeError, "protected workflow files"):
            self.bridge.request_llm_agent(
                self.project_root,
                agent_name="argumentagent",
                task="part3_candidate_argument_design",
                skill="part3-argument-generate",
                output_ref="outputs/part3/candidate_argument_trees",
                input_paths=[],
                instructions=[],
            )

        self.assertEqual({"status": "before"}, self.read_json("runtime/state.json"))
        self.assertFalse((self.project_root / "outputs/part3/argument_tree.json").exists())
        self.assertFalse((self.project_root / "process-memory/20260417_bad_gate.json").exists())

    def test_request_restores_protected_directory_replaced_by_symlink(self):
        self.write_json("outputs/part5/citation_map.json", {"status": "before"})
        fake_agent = self.project_root / "fake_symlink_argumentagent.py"
        fake_agent.write_text(
            (
                "import json, pathlib, shutil, sys\n"
                "request = json.load(sys.stdin)\n"
                "root = pathlib.Path(request['project_root'])\n"
                "outside = root / 'outside_target'\n"
                "outside.mkdir(parents=True, exist_ok=True)\n"
                "part5 = root / 'outputs' / 'part5'\n"
                "shutil.rmtree(part5)\n"
                "part5.symlink_to(outside, target_is_directory=True)\n"
                "(part5 / 'citation_map.json').write_text('{\"status\":\"mutated\"}', encoding='utf-8')\n"
                "print(json.dumps({'proposal': 'done'}, ensure_ascii=False))\n"
            ),
            encoding="utf-8",
        )
        os.environ["RTM_ARGUMENTAGENT_COMMAND"] = f"{sys.executable} {fake_agent}"

        with self.assertRaisesRegex(RuntimeError, "protected workflow files"):
            self.bridge.request_llm_agent(
                self.project_root,
                agent_name="argumentagent",
                task="part3_candidate_argument_design",
                skill="part3-argument-generate",
                output_ref="outputs/part3/candidate_argument_trees",
                input_paths=[],
                instructions=[],
            )

        part5 = self.project_root / "outputs" / "part5"
        self.assertTrue(part5.is_dir())
        self.assertFalse(part5.is_symlink())
        self.assertEqual({"status": "before"}, self.read_json("outputs/part5/citation_map.json"))

    def test_request_restores_and_rejects_skill_file_writes(self):
        skill_path = self.project_root / "skills" / "part6-finalize-manuscript" / "SKILL.md"
        skill_path.parent.mkdir(parents=True, exist_ok=True)
        skill_path.write_text("before skill\n", encoding="utf-8")
        fake_agent = self.project_root / "fake_skill_mutating_argumentagent.py"
        fake_agent.write_text(
            (
                "import json, pathlib, sys\n"
                "request = json.load(sys.stdin)\n"
                "root = pathlib.Path(request['project_root'])\n"
                "(root / 'skills' / 'part6-finalize-manuscript' / 'SKILL.md').write_text('mutated skill\\n', encoding='utf-8')\n"
                "print(json.dumps({'proposal': 'done'}, ensure_ascii=False))\n"
            ),
            encoding="utf-8",
        )
        os.environ["RTM_ARGUMENTAGENT_COMMAND"] = f"{sys.executable} {fake_agent}"

        with self.assertRaisesRegex(RuntimeError, "protected workflow files"):
            self.bridge.request_llm_agent(
                self.project_root,
                agent_name="argumentagent",
                task="part3_candidate_argument_design",
                skill="part3-argument-generate",
                output_ref="outputs/part3/candidate_argument_trees",
                input_paths=[],
                instructions=[],
            )

        self.assertEqual("before skill\n", skill_path.read_text(encoding="utf-8"))

    def test_writeagent_request_restores_and_rejects_protected_file_writes(self):
        writer_bridge = load_writer_bridge()
        self.write_json("runtime/state.json", {"status": "before"})
        self.write_json("outputs/part5/citation_map.json", {"status": "before"})
        log_path = self.project_root / "research-wiki" / "log.md"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("before log\n", encoding="utf-8")
        fake_agent = self.project_root / "fake_mutating_writeagent.py"
        fake_agent.write_text(
            (
                "import json, pathlib, sys\n"
                "request = json.load(sys.stdin)\n"
                "root = pathlib.Path(request['project_root'])\n"
                "(root / 'runtime' / 'state.json').write_text('{\"status\":\"mutated\"}', encoding='utf-8')\n"
                "(root / 'outputs' / 'part5' / 'citation_map.json').write_text('{\"status\":\"mutated\"}', encoding='utf-8')\n"
                "(root / 'research-wiki' / 'log.md').write_text('mutated log\\n', encoding='utf-8')\n"
                "(root / 'outputs' / 'part3').mkdir(parents=True, exist_ok=True)\n"
                "(root / 'outputs' / 'part3' / 'candidate_comparison.json').write_text('{\"bad\":true}', encoding='utf-8')\n"
                "print(json.dumps({'body': '公开正文'}, ensure_ascii=False))\n"
            ),
            encoding="utf-8",
        )
        os.environ["RTM_WRITEAGENT_COMMAND"] = f"{sys.executable} {fake_agent}"
        os.environ["RTM_WRITEAGENT_TIMEOUT"] = "5"

        with self.assertRaisesRegex(RuntimeError, "protected workflow files"):
            writer_bridge.request_writeagent(
                self.project_root,
                task="part6_finalize_manuscript",
                skill="part6-finalize-manuscript",
                output_ref="outputs/part6/writer_body.md",
                input_paths=[],
                instructions=[],
            )

        self.assertEqual({"status": "before"}, self.read_json("runtime/state.json"))
        self.assertEqual({"status": "before"}, self.read_json("outputs/part5/citation_map.json"))
        self.assertEqual("before log\n", log_path.read_text(encoding="utf-8"))
        self.assertFalse((self.project_root / "outputs/part3/candidate_comparison.json").exists())

    def test_write_llm_agent_provenance_records_required_fields(self):
        fake_agent = self.project_root / "fake_argumentagent.py"
        fake_agent.write_text("print('{}')\n", encoding="utf-8")
        os.environ["RTM_ARGUMENTAGENT_COMMAND"] = f"{sys.executable} {fake_agent}"

        self.bridge.write_llm_agent_provenance(
            self.project_root,
            "outputs/part3/argumentagent_provenance.json",
            agent_name="argumentagent",
            task="part3_compare_candidates",
            skill="part3-argument-compare",
            output_ref="outputs/part3/comparison.json",
            mode="llm",
        )

        provenance = self.read_json("outputs/part3/argumentagent_provenance.json")
        self.assertEqual("argumentagent", provenance["agent_name"])
        self.assertEqual("part3_compare_candidates", provenance["task"])
        self.assertEqual("part3-argument-compare", provenance["skill"])
        self.assertEqual("outputs/part3/comparison.json", provenance["output_ref"])
        self.assertEqual("llm", provenance["mode"])
        self.assertTrue(provenance["command_configured"])
        self.assertEqual(Path(sys.executable).name, provenance["command_name"])
        self.assertTrue(provenance["does_not_confirm_human_gate"])


if __name__ == "__main__":
    unittest.main()
