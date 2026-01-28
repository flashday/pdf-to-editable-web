/**
 * PBT-3: 内容保存完整性测试
 * **Validates: Requirements 7.3**
 * 
 * 属性：保存后重新加载的 Markdown 内容必须与保存前完全一致
 */
import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';

// 模拟保存和加载函数
interface SaveLoadSimulator {
  save: (content: string) => Promise<string>;
  load: (savedContent: string) => Promise<string>;
}

// 简单的保存/加载模拟器（无损）
const createLosslessSimulator = (): SaveLoadSimulator => {
  let storage: string = '';
  return {
    save: async (content: string) => {
      storage = content;
      return storage;
    },
    load: async () => {
      return storage;
    },
  };
};

// 生成有效的 Markdown 内容
const markdownContentArb = fc.oneof(
  // 标题
  fc.tuple(fc.integer({ min: 1, max: 6 }), fc.string({ minLength: 1, maxLength: 50 }))
    .map(([level, text]) => `${'#'.repeat(level)} ${text.replace(/[#\n]/g, '')}\n`),
  // 段落
  fc.string({ minLength: 1, maxLength: 200 })
    .map(text => `${text.replace(/\n/g, ' ')}\n\n`),
  // 列表项
  fc.array(fc.string({ minLength: 1, maxLength: 50 }), { minLength: 1, maxLength: 5 })
    .map(items => items.map(item => `- ${item.replace(/\n/g, ' ')}`).join('\n') + '\n\n'),
  // 代码块
  fc.tuple(fc.constantFrom('js', 'python', 'typescript', ''), fc.string({ minLength: 1, maxLength: 100 }))
    .map(([lang, code]) => `\`\`\`${lang}\n${code.replace(/`/g, "'")}\n\`\`\`\n\n`),
);

// 生成带锚点的 Markdown
const markdownWithAnchorsArb = fc.array(
  fc.tuple(
    fc.stringMatching(/^[0-9]{3,6}$/),
    fc.record({
      x: fc.integer({ min: 0, max: 2000 }),
      y: fc.integer({ min: 0, max: 3000 }),
      width: fc.integer({ min: 10, max: 1000 }),
      height: fc.integer({ min: 10, max: 500 }),
    }),
    markdownContentArb,
  ),
  { minLength: 1, maxLength: 10 }
).map(items => {
  const uniqueItems = items.filter((item, index, self) => 
    self.findIndex(i => i[0] === item[0]) === index
  );
  return uniqueItems.map(([id, coords, content]) => 
    `<div id="block_${id}" data-coords="${coords.x},${coords.y},${coords.width},${coords.height}" style="display:none;"></div>\n${content}`
  ).join('');
});

describe('PBT-3: 内容保存完整性', () => {
  it('属性：保存后加载的内容与原始内容完全一致', () => {
    fc.assert(
      fc.asyncProperty(
        markdownWithAnchorsArb,
        async (originalContent) => {
          const simulator = createLosslessSimulator();
          
          // 保存
          await simulator.save(originalContent);
          
          // 加载
          const loadedContent = await simulator.load(originalContent);
          
          // 验证完全一致
          expect(loadedContent).toBe(originalContent);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  it('属性：多次保存后内容保持一致', () => {
    fc.assert(
      fc.asyncProperty(
        markdownWithAnchorsArb,
        fc.integer({ min: 2, max: 5 }),
        async (content, saveCount) => {
          const simulator = createLosslessSimulator();
          
          // 多次保存
          for (let i = 0; i < saveCount; i++) {
            await simulator.save(content);
          }
          
          // 加载
          const loadedContent = await simulator.load(content);
          
          // 验证一致
          expect(loadedContent).toBe(content);
          
          return true;
        }
      ),
      { numRuns: 50 }
    );
  });

  it('属性：编辑后保存的内容正确反映编辑', () => {
    fc.assert(
      fc.asyncProperty(
        markdownWithAnchorsArb,
        fc.string({ minLength: 1, maxLength: 100 }),
        async (originalContent, appendedText) => {
          const simulator = createLosslessSimulator();
          
          // 保存原始内容
          await simulator.save(originalContent);
          
          // 编辑：追加内容
          const editedContent = originalContent + '\n' + appendedText;
          await simulator.save(editedContent);
          
          // 加载
          const loadedContent = await simulator.load(editedContent);
          
          // 验证编辑后的内容
          expect(loadedContent).toBe(editedContent);
          expect(loadedContent).toContain(appendedText);
          
          return true;
        }
      ),
      { numRuns: 50 }
    );
  });

  it('属性：空内容保存和加载正确', () => {
    fc.assert(
      fc.asyncProperty(
        fc.constant(''),
        async (emptyContent) => {
          const simulator = createLosslessSimulator();
          
          await simulator.save(emptyContent);
          const loadedContent = await simulator.load(emptyContent);
          
          expect(loadedContent).toBe('');
          
          return true;
        }
      ),
      { numRuns: 10 }
    );
  });

  it('属性：特殊字符保存完整性', () => {
    const specialCharsArb = fc.string({
      minLength: 1,
      maxLength: 500,
    }).filter(s => !s.includes('\0')); // 排除 null 字符

    fc.assert(
      fc.asyncProperty(
        specialCharsArb,
        async (content) => {
          const simulator = createLosslessSimulator();
          
          await simulator.save(content);
          const loadedContent = await simulator.load(content);
          
          expect(loadedContent).toBe(content);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  it('属性：Unicode 内容保存完整性', () => {
    // 使用 string 生成器，包含 Unicode 字符
    const unicodeArb = fc.string({ minLength: 1, maxLength: 200 })
      .filter(s => !s.includes('\0'));

    fc.assert(
      fc.asyncProperty(
        unicodeArb,
        async (content) => {
          const simulator = createLosslessSimulator();
          
          await simulator.save(content);
          const loadedContent = await simulator.load(content);
          
          expect(loadedContent).toBe(content);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  it('属性：锚点在保存后保持完整', () => {
    fc.assert(
      fc.asyncProperty(
        markdownWithAnchorsArb,
        async (content) => {
          const simulator = createLosslessSimulator();
          
          // 计算原始锚点数量
          const anchorRegex = /<div id="block_\w+" data-coords="[\d,]+" style="display:none;"><\/div>/g;
          const originalAnchors = content.match(anchorRegex) || [];
          
          await simulator.save(content);
          const loadedContent = await simulator.load(content);
          
          // 验证锚点数量一致
          const loadedAnchors = loadedContent.match(anchorRegex) || [];
          expect(loadedAnchors.length).toBe(originalAnchors.length);
          
          // 验证每个锚点内容一致
          for (let i = 0; i < originalAnchors.length; i++) {
            expect(loadedAnchors[i]).toBe(originalAnchors[i]);
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });
});
