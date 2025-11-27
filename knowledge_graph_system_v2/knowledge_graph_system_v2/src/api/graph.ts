import { get, post } from "./http";
import type { GraphDTO } from "@/types/graph";

// 后端原始节点/边结构（Neo4j -> FastAPI -> 前端）
export interface RawNode {
  id: string;
  label: string;
  properties: Record<string, any>;
}

export interface RawEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  properties: Record<string, any>;
}

export interface GraphResponse {
  nodes: RawNode[];
  edges: RawEdge[];
}

export interface RootGraphParams {
  limit?: number;
  yearStart?: number;
  yearEnd?: number;
  orgs?: string[];
  author?: string;
}

// 获取根图谱
export const fetchRootGraph = (params: RootGraphParams) =>
  get<GraphResponse>("/graph/root", params);

// 获取某个节点的子图
export const fetchChildrenGraph = (nodeId: string) =>
  get<GraphResponse>(`/graph/children/${nodeId}`);

// 持久化布局
export const persistLayout = (positions: { node_id: string; x: number; y: number }[]) =>
  post("/graph/layout/persist", { positions });
