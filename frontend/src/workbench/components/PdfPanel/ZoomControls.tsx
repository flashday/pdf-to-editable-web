import React from 'react';
import styles from './ZoomControls.module.css';

interface ZoomControlsProps {
  zoomLevel: number;
  onZoomChange: (level: number) => void;
}

const ZOOM_PRESETS = [50, 75, 100, 125, 150, 200];

const ZoomControls: React.FC<ZoomControlsProps> = ({ zoomLevel, onZoomChange }) => {
  const handleZoomIn = () => {
    onZoomChange(Math.min(zoomLevel + 10, 200));
  };

  const handleZoomOut = () => {
    onZoomChange(Math.max(zoomLevel - 10, 50));
  };

  const handlePresetChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onZoomChange(parseInt(e.target.value, 10));
  };

  const handleFitWidth = () => {
    // 适应宽度 - 这里简化为 100%
    onZoomChange(100);
  };

  return (
    <div className={styles.container}>
      <button 
        className={styles.button}
        onClick={handleZoomOut}
        disabled={zoomLevel <= 50}
        title="缩小 (Ctrl+滚轮)"
      >
        −
      </button>
      
      <select 
        className={styles.select}
        value={zoomLevel}
        onChange={handlePresetChange}
      >
        {ZOOM_PRESETS.map(preset => (
          <option key={preset} value={preset}>
            {preset}%
          </option>
        ))}
        {!ZOOM_PRESETS.includes(zoomLevel) && (
          <option value={zoomLevel}>{zoomLevel}%</option>
        )}
      </select>
      
      <button 
        className={styles.button}
        onClick={handleZoomIn}
        disabled={zoomLevel >= 200}
        title="放大 (Ctrl+滚轮)"
      >
        +
      </button>
      
      <button 
        className={styles.fitButton}
        onClick={handleFitWidth}
        title="适应宽度"
      >
        ⊡
      </button>
    </div>
  );
};

export default ZoomControls;
