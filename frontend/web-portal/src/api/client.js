const API_BASE = '/api/v1';

export const apiClient = {
  async getHealth() {
    try {
      const res = await fetch(`${API_BASE}/health/ready`);
      return await res.json();
    } catch (err) {
      return { status: 'OFFLINE', ready: false };
    }
  },

  async getSummary() {
    const res = await fetch(`${API_BASE}/analytics/summary`);
    if (!res.ok) throw new Error('Failed to fetch analytics summary');
    return await res.json();
  },

  async getHotspots() {
    const res = await fetch(`${API_BASE}/analytics/hotspots`);
    if (!res.ok) throw new Error('Failed to fetch hotspots');
    return await res.json();
  },

  async getViolations(params = {}) {
    const query = new URLSearchParams(params).toString();
    const res = await fetch(`${API_BASE}/violations?${query}`);
    if (!res.ok) throw new Error('Failed to fetch violations');
    return await res.json();
  },

  async getChallans(params = {}) {
    const query = new URLSearchParams(params).toString();
    const res = await fetch(`${API_BASE}/violations/challans?${query}`);
    if (!res.ok) throw new Error('Failed to fetch challans');
    return await res.json();
  },

  async getChallanById(idOrPlate) {
    const res = await fetch(`${API_BASE}/violations/challans/${encodeURIComponent(idOrPlate)}`);
    if (!res.ok) {
      if (res.status === 404) return null;
      throw new Error('Challan lookup failed');
    }
    return await res.json();
  },

  async payChallan(challanNumber) {
    const res = await fetch(`${API_BASE}/violations/challans/${encodeURIComponent(challanNumber)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: 'PAID' })
    });
    if (!res.ok) throw new Error('Failed to update challan');
    return await res.json();
  },

  async submitCitizenReport(reportData, idempotencyKey) {
    const headers = { 'Content-Type': 'application/json' };
    if (idempotencyKey) {
      headers['Idempotency-Key'] = idempotencyKey;
    }
    const res = await fetch(`${API_BASE}/citizen-reports`, {
      method: 'POST',
      headers,
      body: JSON.stringify(reportData)
    });
    if (!res.ok) throw new Error('Failed to submit citizen report');
    return await res.json();
  },

  async getCitizenReports(params = {}) {
    const query = new URLSearchParams(params).toString();
    const res = await fetch(`${API_BASE}/citizen-reports?${query}`);
    if (!res.ok) throw new Error('Failed to fetch citizen reports');
    return await res.json();
  },

  async getCitizenReportByTicket(ticketId) {
    const res = await fetch(`${API_BASE}/citizen-reports/${encodeURIComponent(ticketId)}`);
    if (!res.ok) {
      if (res.status === 404) return null;
      throw new Error('Report ticket not found');
    }
    return await res.json();
  },

  async updateCitizenReport(ticketId, updateData) {
    const res = await fetch(`${API_BASE}/citizen-reports/${encodeURIComponent(ticketId)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updateData)
    });
    if (!res.ok) throw new Error('Failed to update report');
    return await res.json();
  },

  async triggerEdgeSimulationEvent() {
    const res = await fetch(`${API_BASE}/violations/ingest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        event_id: 'ui_sim_' + Math.random().toString(36).substring(7),
        camera_id: 'CAM-INTERACTIVE-01',
        location_name: 'Central Junction Demo',
        zone_id: 'ZONE-CENTRAL-01',
        timestamp: new Date().toISOString(),
        violation_type: ['NO_HELMET', 'TRIPLE_RIDING', 'SPEEDING'][Math.floor(Math.random() * 3)],
        confidence: 0.94,
        raw_plate_text: 'KA0' + (Math.floor(Math.random() * 8) + 1) + 'AB' + Math.floor(1000 + Math.random() * 9000),
        detected_objects: []
      })
    });
    return await res.json();
  }
};
