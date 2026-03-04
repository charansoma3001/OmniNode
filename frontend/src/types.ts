/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

export type SegmentType = 'ZONE 1' | 'ZONE 2' | 'ZONE 3' | 'GLOBAL';

export interface NetworkNode {
  id: string;
  name: string;
  type: SegmentType;
  status: 'NOMINAL' | 'WARNING' | 'CRITICAL';
  location: { lat: number; lng: number };
  telemetry: {
    voltage: string;
    loadMw: string;
    genMw: string;
    frequency: string;
  };
}

export interface Agent {
  id: string;
  name: string;
  role: string;
  status: 'IDLE' | 'ACTIVE' | 'ERROR' | 'DEPLOYING';
  hierarchyLevel: number;
  parentId?: string;
  embodiment?: string; // The physical system it's currently controlling
  tasks: string[];
}

export interface SigintEvent {
  id: string;
  timestamp: string;
  frequency: string;
  location: { lat: number; lng: number };
  confidence: number;
  type: 'EMISSION' | 'INTERCEPT' | 'GEOLOCATION';
}
