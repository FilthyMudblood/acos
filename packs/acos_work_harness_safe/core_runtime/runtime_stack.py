import hashlib
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

import numpy as np

ToolHandler = Callable[..., Awaitable[Dict[str, Any]]]
EmbeddingProvider = Callable[[str], np.ndarray]


@dataclass(frozen=True)
class RuntimeControlConfig:
    embedding_dim: int = 64
    max_context_tools: int = 8
    base_pruning_threshold: float = 0.10
    hard_drift_threshold: float = 0.92
    state_restricted_threshold: float = 0.70
    state_safe_mode_threshold: float = 0.85


DEFAULT_RUNTIME_CONTROL_CONFIG = RuntimeControlConfig()


def stable_text_embedding(text: str, dim: int = 64) -> np.ndarray:
    """Deterministic lightweight embedding with L2 normalization."""
    if dim <= 0:
        raise ValueError("embedding dim must be positive")
    vec = np.zeros(dim, dtype=float)
    normalized = str(text or "").lower().replace("_", " ")
    terms = [tok for tok in normalized.split() if tok]
    if not terms:
        vec[0] = 1.0
        return vec

    for term in terms:
        digest = hashlib.sha256(term.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:8], byteorder="big", signed=False) % dim
        vec[idx] += 1.0
    norm = float(np.linalg.norm(vec))
    if norm > 0.0:
        vec /= norm
    return vec


def compute_similarity_scores(target_vector: np.ndarray, tool_matrix: np.ndarray) -> np.ndarray:
    """Hot path: pure vector math only."""
    return np.dot(tool_matrix, target_vector)


@dataclass(frozen=True)
class CompiledToolMatrix:
    tool_names: List[str]
    matrix: np.ndarray

    def as_tuple(self) -> Tuple[List[str], np.ndarray]:
        return (list(self.tool_names), self.matrix)


class EmbeddingRegistry:
    """Cold-path tool embedding registry."""

    def __init__(self, compiled: CompiledToolMatrix) -> None:
        if compiled.matrix.ndim != 2:
            raise ValueError("compiled tool matrix must be a 2D numpy array")
        if len(compiled.tool_names) != compiled.matrix.shape[0]:
            raise ValueError("tool_names length must match matrix row count")
        self._compiled = compiled

    def get_compiled_tool_matrix(self) -> Tuple[List[str], np.ndarray]:
        return self._compiled.as_tuple()

    @classmethod
    def compile_from_provider(
        cls,
        tool_names: List[str],
        embedding_provider: EmbeddingProvider,
    ) -> "EmbeddingRegistry":
        vectors = [embedding_provider(name) for name in tool_names]
        matrix = np.vstack(vectors).astype(float)
        return cls(CompiledToolMatrix(tool_names=list(tool_names), matrix=matrix))

    @classmethod
    def from_precomputed(
        cls,
        tool_names: List[str],
        matrix: np.ndarray,
    ) -> "EmbeddingRegistry":
        return cls(CompiledToolMatrix(tool_names=list(tool_names), matrix=matrix.astype(float)))


class ObjectiveEmbeddingProvider:
    """Cold-path objective embedding provider abstraction."""

    def __init__(self, provider: EmbeddingProvider) -> None:
        self._provider = provider

    def get_objective_embedding(self, objective_text: str) -> np.ndarray:
        vector = np.asarray(self._provider(objective_text), dtype=float)
        if vector.ndim != 1:
            raise ValueError("objective embedding must be a 1D numpy array")
        return vector

    @classmethod
    def from_precomputed_map(
        cls,
        embeddings_by_text: Dict[str, np.ndarray],
        *,
        default_embedding: Optional[np.ndarray] = None,
    ) -> "ObjectiveEmbeddingProvider":
        def _provider(text: str) -> np.ndarray:
            if text in embeddings_by_text:
                return embeddings_by_text[text]
            if default_embedding is not None:
                return default_embedding
            raise KeyError(f"objective embedding not found for text: {text}")

        return cls(_provider)


def align_compiled_matrix_to_tools(
    tool_handlers: Dict[str, object],
    compiled_tool_names: List[str],
    compiled_matrix: np.ndarray,
) -> Tuple[List[str], np.ndarray]:
    """Align externally compiled matrix rows to runtime tool order."""
    row_index = {name: i for i, name in enumerate(compiled_tool_names)}
    ordered_names = list(tool_handlers.keys())
    try:
        rows = [compiled_matrix[row_index[name]] for name in ordered_names]
    except KeyError as exc:
        missing = str(exc).strip("'")
        raise ValueError(f"compiled embedding matrix missing runtime tool: {missing}") from exc
    return ordered_names, np.vstack(rows).astype(float)


@dataclass(frozen=True)
class Tool:
    """Runtime tool contract with capability lock fields."""

    name: str
    handler: ToolHandler
    capabilities: set[str]
    embedding: np.ndarray


@dataclass(frozen=True)
class ToolSpec:
    """Configurable physical tool definition."""

    name: str
    handler: ToolHandler
    capabilities: set[str] = field(default_factory=lambda: {"read"})
    description: str = ""
    criticality_score: float = 0.45
    embedding: Optional[np.ndarray] = None


class PhysicalToolRegistry:
    """Runtime registry for physical tool execution and sandbox metadata."""

    def __init__(self, tool_specs: list[ToolSpec]) -> None:
        if not tool_specs:
            raise ValueError("PhysicalToolRegistry requires at least one tool.")
        names = [spec.name for spec in tool_specs]
        if len(names) != len(set(names)):
            raise ValueError("PhysicalToolRegistry tool names must be unique.")
        self._specs = list(tool_specs)
        self._by_name = {spec.name: spec for spec in self._specs}

    @classmethod
    def from_handlers(
        cls,
        tool_handlers: Dict[str, ToolHandler],
        *,
        capability_map: Optional[Dict[str, set[str]]] = None,
        criticality_map: Optional[Dict[str, float]] = None,
    ) -> "PhysicalToolRegistry":
        specs: list[ToolSpec] = []
        for name, handler in tool_handlers.items():
            specs.append(
                ToolSpec(
                    name=name,
                    handler=handler,
                    capabilities=set((capability_map or {}).get(name, {"read"})),
                    criticality_score=float((criticality_map or {}).get(name, 0.45)),
                )
            )
        return cls(specs)

    def get_handler(self, name: str) -> Optional[ToolHandler]:
        spec = self._by_name.get(name)
        return spec.handler if spec is not None else None

    def get_spec(self, name: str) -> Optional[ToolSpec]:
        return self._by_name.get(name)

    def get_tool_names(self) -> list[str]:
        return [spec.name for spec in self._specs]

    def as_handler_map(self) -> Dict[str, ToolHandler]:
        return {spec.name: spec.handler for spec in self._specs}

    def as_capability_map(self) -> Dict[str, set[str]]:
        return {spec.name: set(spec.capabilities) for spec in self._specs}

    def as_criticality_map(self) -> Dict[str, float]:
        return {spec.name: float(spec.criticality_score) for spec in self._specs}


class GlobalToolRegistry:
    """In-memory tool registry with cached embedding matrix."""

    def __init__(self, tools: list[Tool]) -> None:
        if not tools:
            raise ValueError("GlobalToolRegistry requires at least one tool.")
        self._tools = list(tools)
        self._name_to_tool = {tool.name: tool for tool in self._tools}
        self._embedding_matrix_cache = np.vstack([tool.embedding for tool in self._tools]).astype(float)

    def get_embedding_matrix(self) -> np.ndarray:
        return self._embedding_matrix_cache

    def get_tool_by_index(self, idx: int) -> Tool:
        return self._tools[idx]

    def get_tool_by_name(self, name: str) -> Optional[Tool]:
        return self._name_to_tool.get(name)

    def get_tool_names(self) -> list[str]:
        return [tool.name for tool in self._tools]


@dataclass
class RootObjectiveTensor:
    objective_text: str
    embedding_dim: int = DEFAULT_RUNTIME_CONTROL_CONFIG.embedding_dim
    embedding_vector: Optional[np.ndarray] = None
    _embedding: np.ndarray = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.embedding_vector is not None:
            vector = np.asarray(self.embedding_vector, dtype=float)
            if vector.ndim != 1:
                raise ValueError("embedding_vector must be a 1D numpy array")
            self._embedding = vector
            return
        self._embedding = stable_text_embedding(self.objective_text, dim=self.embedding_dim)

    def get_normalized_embedding(self) -> np.ndarray:
        return self._embedding


class RuntimeStateBus:
    """State-machine contract for phase capability output."""

    def __init__(self, config: RuntimeControlConfig = DEFAULT_RUNTIME_CONTROL_CONFIG) -> None:
        self._config = config
        self.current_phase = "READ"
        self._read_completion_tools = {"read_file"}
        self._action_tools = {"create_jira_ticket"}

    def on_tool_observation(self, tool_name: str, succeeded: bool) -> None:
        """
        Phase transition driven by runtime observation, not prompt regex.
        READ -> ACTION when information-ingestion tool completes successfully.
        """
        if not succeeded:
            return
        normalized = str(tool_name or "").strip().lower()
        if normalized in self._read_completion_tools:
            self.current_phase = "ACTION"
            return
        if normalized in self._action_tools:
            self.current_phase = "ACTION"

    def get_current_phase_capabilities(self, logical_entropy: float, conflict_score: float) -> set[str]:
        if self.current_phase == "ACTION":
            caps = {"read", "query", "lookup", "act", "refund", "write"}
        else:
            caps = {"read", "query", "lookup"}

        if (
            logical_entropy > self._config.state_safe_mode_threshold
            or conflict_score > self._config.state_safe_mode_threshold
        ):
            self.current_phase = "SAFE_MODE"
            return {"read", "query", "lookup"}
        if (
            logical_entropy > self._config.state_restricted_threshold
            or conflict_score > self._config.state_restricted_threshold
        ):
            self.current_phase = "RESTRICTED"
            return {"read", "query", "lookup", "act"} if "act" in caps else {"read", "query", "lookup"}
        return caps


def build_global_tool_registry(
    tool_handlers: Dict[str, ToolHandler],
    config: RuntimeControlConfig = DEFAULT_RUNTIME_CONTROL_CONFIG,
    compiled_tool_matrix: Optional[Tuple[list[str], np.ndarray]] = None,
    capability_map: Optional[Dict[str, set[str]]] = None,
) -> GlobalToolRegistry:
    default_capability_map: Dict[str, set[str]] = {
        "query_db": {"read", "query", "lookup"},
        "refund_lookup": {"read", "lookup", "act", "refund"},
        "faulty_query_db": {"read", "query", "lookup"},
        "timeout_refund": {"read", "lookup", "act", "refund"},
        "read_file": {"read", "lookup"},
        "create_jira_ticket": {"act", "write"},
    }
    resolved_capability_map = dict(default_capability_map)
    if capability_map:
        resolved_capability_map.update({name: set(caps) for name, caps in capability_map.items()})
    tools: list[Tool] = []
    external_embeddings: Dict[str, np.ndarray] = {}
    if compiled_tool_matrix is not None:
        compiled_names, compiled_matrix = compiled_tool_matrix
        ordered_names, aligned = align_compiled_matrix_to_tools(tool_handlers, compiled_names, compiled_matrix)
        external_embeddings = {name: aligned[idx] for idx, name in enumerate(ordered_names)}

    for name, handler in tool_handlers.items():
        caps = set(resolved_capability_map.get(name, {"read"}))
        embedding = external_embeddings.get(name)
        if embedding is None:
            embedding = stable_text_embedding(name, dim=config.embedding_dim)
        tools.append(Tool(name=name, handler=handler, capabilities=caps, embedding=embedding))
    return GlobalToolRegistry(tools)


def prepare_sandbox_environment(
    dynamic_threshold: float,
    current_phase_caps: set[str],
    root_objective_tensor: RootObjectiveTensor,
    global_tool_registry: GlobalToolRegistry,
    max_context_tools: int = 8,
) -> list[str]:
    """Dual-lock pruning: semantic threshold + capability lock + top-k."""
    target_vector = root_objective_tensor.get_normalized_embedding()
    tool_matrix = global_tool_registry.get_embedding_matrix()
    similarity_scores = compute_similarity_scores(target_vector=target_vector, tool_matrix=tool_matrix)
    surviving_tools: list[tuple[float, Tool]] = []
    surviving_names: set[str] = set()
    read_only_candidates: list[tuple[float, Tool]] = []
    for idx, score in enumerate(similarity_scores):
        if score < dynamic_threshold:
            continue

        tool = global_tool_registry.get_tool_by_index(idx)
        if not tool.capabilities.issubset(current_phase_caps):
            continue
        if "read" in tool.capabilities and "act" not in tool.capabilities:
            read_only_candidates.append((float(score), tool))
        surviving_tools.append((float(score), tool))
        surviving_names.add(tool.name)

    # Minimum viable tool coverage:
    # avoid over-pruning normal multi-step workflows (e.g. read -> create ticket).
    min_coverage = min(3, len(global_tool_registry.get_tool_names()))
    if len(surviving_tools) < min_coverage:
        for idx, score in enumerate(similarity_scores):
            tool = global_tool_registry.get_tool_by_index(idx)
            if tool.name in surviving_names:
                continue
            if not tool.capabilities.issubset(current_phase_caps):
                continue
            surviving_tools.append((float(score), tool))
            surviving_names.add(tool.name)
            if len(surviving_tools) >= min_coverage:
                break

    # In READ-like phases, keep at least one pure read ingestion tool to avoid
    # unauthorized action loops before phase transition.
    if "act" not in current_phase_caps and read_only_candidates:
        read_only_candidates.sort(key=lambda x: x[0], reverse=True)
        top_read = read_only_candidates[0][1]
        if top_read.name not in surviving_names:
            surviving_tools.append((read_only_candidates[0][0], top_read))
            surviving_names.add(top_read.name)

    surviving_tools.sort(key=lambda x: x[0], reverse=True)
    return [entry[1].name for entry in surviving_tools[:max_context_tools]]
