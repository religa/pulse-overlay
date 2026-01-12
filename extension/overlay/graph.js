/**
 * PulseGraph - Real-time heart rate graph component.
 */

class PulseGraph {
  constructor(canvas, duration = 60) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.duration = duration; // seconds
    this.points = [];
    this.minBpm = 40;
    this.maxBpm = 200;
    this.draw(); // Draw baseline immediately
  }

  /**
   * Add a data point to the graph.
   */
  addPoint(bpm, timestamp) {
    const now = Date.now();
    this.points.push({ bpm, timestamp: timestamp || now });

    // Remove old points
    const cutoff = now - this.duration * 1000;
    this.points = this.points.filter(p => p.timestamp > cutoff);

    // Update min/max based on current data (clamp to valid range)
    if (this.points.length > 0) {
      const bpms = this.points.map(p => Math.max(40, Math.min(220, p.bpm)));
      const min = Math.min(...bpms);
      const max = Math.max(...bpms);
      this.minBpm = Math.max(40, min - 10);
      this.maxBpm = Math.min(220, max + 10);
    }

    this.draw();
  }

  /**
   * Draw the graph.
   */
  draw() {
    const { canvas, ctx, points } = this;
    const width = canvas.width;
    const height = canvas.height;

    // Clear canvas
    ctx.clearRect(0, 0, width, height);

    // Draw baseline when no data
    if (points.length < 2) {
      ctx.strokeStyle = 'rgba(244, 67, 54, 0.3)';
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(0, height / 2);
      ctx.lineTo(width, height / 2);
      ctx.stroke();
      ctx.setLineDash([]);
      return;
    }

    const now = Date.now();
    const startTime = now - this.duration * 1000;
    // Prevent divide by zero when all points have same BPM
    const bpmRange = Math.max(1, this.maxBpm - this.minBpm);

    // Draw line
    ctx.beginPath();
    ctx.strokeStyle = '#F44336';
    ctx.lineWidth = 2;
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';

    let first = true;
    for (const point of points) {
      const x = ((point.timestamp - startTime) / (this.duration * 1000)) * width;
      const y = height - ((point.bpm - this.minBpm) / bpmRange) * height;

      if (first) {
        ctx.moveTo(x, y);
        first = false;
      } else {
        ctx.lineTo(x, y);
      }
    }

    ctx.stroke();

    // Draw gradient fill under the line
    ctx.lineTo(width, height);
    ctx.lineTo(0, height);
    ctx.closePath();

    const gradient = ctx.createLinearGradient(0, 0, 0, height);
    gradient.addColorStop(0, 'rgba(244, 67, 54, 0.3)');
    gradient.addColorStop(1, 'rgba(244, 67, 54, 0)');
    ctx.fillStyle = gradient;
    ctx.fill();
  }

  /**
   * Clear the graph.
   */
  clear() {
    this.points = [];
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
  }
}

// Export for overlay
window.PulseGraph = PulseGraph;
