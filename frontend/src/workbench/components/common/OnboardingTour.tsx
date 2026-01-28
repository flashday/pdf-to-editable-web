/**
 * 操作引导教程组件
 * 任务 21.4: 添加操作引导教程（首次使用）
 */
import React, { useState, useEffect, useCallback } from 'react';
import styles from './OnboardingTour.module.css';

interface TourStep {
  target: string; // CSS 选择器
  title: string;
  content: string;
  position: 'top' | 'bottom' | 'left' | 'right';
}

const TOUR_STEPS: TourStep[] = [
  {
    target: '.pdf-panel',
    title: '📄 PDF 预览区',
    content: '这里显示原始 PDF 文档的图像。点击任意文本区域可以快速定位到编辑器中对应的位置。',
    position: 'right',
  },
  {
    target: '.bounding-box-overlay',
    title: '🎯 识别区域',
    content: '彩色边框表示 OCR 识别的文本区域。绿色=高置信度，黄色=中等，红色=低置信度（需要检查）。',
    position: 'right',
  },
  {
    target: '.editor-panel',
    title: '✏️ Markdown 编辑器',
    content: '在这里编辑识别后的文本。支持所见即所得编辑，也可以切换到源码模式。',
    position: 'left',
  },
  {
    target: '.zoom-controls',
    title: '🔍 缩放控制',
    content: '使用这些按钮调整 PDF 预览的缩放级别，方便查看细节。',
    position: 'bottom',
  },
  {
    target: '.save-button',
    title: '💾 保存文档',
    content: '编辑完成后点击保存，或使用 Ctrl+S 快捷键。系统也会自动保存您的更改。',
    position: 'bottom',
  },
  {
    target: '.sync-scroll-toggle',
    title: '🔗 同步滚动',
    content: '开启后，PDF 和编辑器会同步滚动，方便对照编辑。',
    position: 'bottom',
  },
];

const STORAGE_KEY = 'workbench_tour_completed';

interface OnboardingTourProps {
  onComplete?: () => void;
  forceShow?: boolean;
}

export const OnboardingTour: React.FC<OnboardingTourProps> = ({
  onComplete,
  forceShow = false,
}) => {
  const [isActive, setIsActive] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [targetRect, setTargetRect] = useState<DOMRect | null>(null);

  // 检查是否首次使用
  useEffect(() => {
    if (forceShow) {
      setIsActive(true);
      return;
    }

    const completed = localStorage.getItem(STORAGE_KEY);
    if (!completed) {
      // 延迟显示，等待页面加载完成
      const timer = setTimeout(() => setIsActive(true), 1000);
      return () => clearTimeout(timer);
    }
  }, [forceShow]);

  // 更新目标元素位置
  useEffect(() => {
    if (!isActive) return;

    const updateTargetRect = () => {
      const step = TOUR_STEPS[currentStep];
      const target = document.querySelector(step.target);
      if (target) {
        setTargetRect(target.getBoundingClientRect());
      } else {
        // 如果找不到目标，跳到下一步
        if (currentStep < TOUR_STEPS.length - 1) {
          setCurrentStep((prev) => prev + 1);
        }
      }
    };

    updateTargetRect();
    window.addEventListener('resize', updateTargetRect);
    window.addEventListener('scroll', updateTargetRect);

    return () => {
      window.removeEventListener('resize', updateTargetRect);
      window.removeEventListener('scroll', updateTargetRect);
    };
  }, [isActive, currentStep]);

  const handleNext = useCallback(() => {
    if (currentStep < TOUR_STEPS.length - 1) {
      setCurrentStep((prev) => prev + 1);
    } else {
      handleComplete();
    }
  }, [currentStep]);

  const handlePrev = useCallback(() => {
    if (currentStep > 0) {
      setCurrentStep((prev) => prev - 1);
    }
  }, [currentStep]);

  const handleSkip = useCallback(() => {
    handleComplete();
  }, []);

  const handleComplete = useCallback(() => {
    setIsActive(false);
    localStorage.setItem(STORAGE_KEY, 'true');
    onComplete?.();
  }, [onComplete]);

  if (!isActive) return null;

  const step = TOUR_STEPS[currentStep];
  const tooltipStyle = getTooltipStyle(targetRect, step.position);

  return (
    <div className={styles.overlay}>
      {/* 高亮遮罩 */}
      {targetRect && (
        <div
          className={styles.spotlight}
          style={{
            top: targetRect.top - 8,
            left: targetRect.left - 8,
            width: targetRect.width + 16,
            height: targetRect.height + 16,
          }}
        />
      )}

      {/* 提示框 */}
      <div
        className={`${styles.tooltip} ${styles[step.position]}`}
        style={tooltipStyle}
      >
        <div className={styles.tooltipHeader}>
          <span className={styles.stepIndicator}>
            {currentStep + 1} / {TOUR_STEPS.length}
          </span>
          <button className={styles.skipButton} onClick={handleSkip}>
            跳过
          </button>
        </div>
        <h3 className={styles.tooltipTitle}>{step.title}</h3>
        <p className={styles.tooltipContent}>{step.content}</p>
        <div className={styles.tooltipFooter}>
          <button
            className={styles.prevButton}
            onClick={handlePrev}
            disabled={currentStep === 0}
          >
            上一步
          </button>
          <button className={styles.nextButton} onClick={handleNext}>
            {currentStep === TOUR_STEPS.length - 1 ? '完成' : '下一步'}
          </button>
        </div>
      </div>
    </div>
  );
};

// 计算提示框位置
function getTooltipStyle(
  targetRect: DOMRect | null,
  position: TourStep['position']
): React.CSSProperties {
  if (!targetRect) {
    return { top: '50%', left: '50%', transform: 'translate(-50%, -50%)' };
  }

  const TOOLTIP_OFFSET = 16;
  const style: React.CSSProperties = {};

  switch (position) {
    case 'top':
      style.bottom = window.innerHeight - targetRect.top + TOOLTIP_OFFSET;
      style.left = targetRect.left + targetRect.width / 2;
      style.transform = 'translateX(-50%)';
      break;
    case 'bottom':
      style.top = targetRect.bottom + TOOLTIP_OFFSET;
      style.left = targetRect.left + targetRect.width / 2;
      style.transform = 'translateX(-50%)';
      break;
    case 'left':
      style.right = window.innerWidth - targetRect.left + TOOLTIP_OFFSET;
      style.top = targetRect.top + targetRect.height / 2;
      style.transform = 'translateY(-50%)';
      break;
    case 'right':
      style.left = targetRect.right + TOOLTIP_OFFSET;
      style.top = targetRect.top + targetRect.height / 2;
      style.transform = 'translateY(-50%)';
      break;
  }

  return style;
}

// Hook: 重置教程
export function useResetTour(): () => void {
  return useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    window.location.reload();
  }, []);
}

// 检查是否已完成教程
export function isTourCompleted(): boolean {
  return localStorage.getItem(STORAGE_KEY) === 'true';
}

export default OnboardingTour;
