/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { NetworkNode, Agent, SegmentType } from './types';

export const SEGMENTS: SegmentType[] = ['ZONE 1', 'ZONE 2', 'ZONE 3', 'GLOBAL'];

export const INITIAL_NODES: NetworkNode[] = [];

export const INITIAL_AGENTS: Agent[] = [
  { id: 'A-ORCH-01', name: 'Strategic Commander', role: 'Global Mission Control', status: 'ACTIVE', hierarchyLevel: 0, tasks: ['Mission Synchronization', 'Resource Allocation', 'Segment Cueing'] },

  { id: 'A-SEG-01', name: 'Zone 1 Control', role: 'Segment Controller', status: 'ACTIVE', hierarchyLevel: 1, parentId: 'A-ORCH-01', tasks: ['Voltage Regulation', 'High-Tempo Ops'] },
  { id: 'A-SEG-02', name: 'Zone 2 Control', role: 'Segment Controller', status: 'ACTIVE', hierarchyLevel: 1, parentId: 'A-ORCH-01', tasks: ['Load Shedding', 'Third-Party Service Reduction'] },
  { id: 'A-SEG-03', name: 'Zone 3 Control', role: 'Segment Controller', status: 'ACTIVE', hierarchyLevel: 1, parentId: 'A-ORCH-01', tasks: ['Industrial Balancing', 'Launch Window Support'] },

  { id: 'A-NODE-01', name: 'Bus 1 Sub-Agent', role: 'Node Controller', status: 'ACTIVE', hierarchyLevel: 2, parentId: 'A-SEG-01', embodiment: 'Bus-1', tasks: ['Telemetry Processing', 'Command Uplink'] },
  { id: 'A-NODE-02', name: 'Bus 5 Sub-Agent', role: 'Node Controller', status: 'ACTIVE', hierarchyLevel: 2, parentId: 'A-SEG-02', embodiment: 'Bus-5', tasks: ['Mobile Tracking', 'Signal Intercept'] },
  { id: 'A-NODE-03', name: 'Bus 12 Sub-Agent', role: 'Node Controller', status: 'ACTIVE', hierarchyLevel: 2, parentId: 'A-SEG-03', embodiment: 'Bus-12', tasks: ['Data Relay', 'Persistent Collection'] },
];
