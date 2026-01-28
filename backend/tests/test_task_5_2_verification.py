"""
Verification tests for Task 5.2: 更新表格内容生成逻辑
Tests the _generate_block_content function for complex and simple table handling.

Requirements validated:
- 3.1: Complex tables preserve original HTML format
- 3.4: Tables with colspan/rowspan output HTML
- 3.5: Simple tables output Markdown format
"""
import sys
sys.path.insert(0, '.')

from backend.api.workbench_routes import _is_complex_table, _generate_block_content


def test_complex_table_with_colspan():
    """Test that tables with colspan > 1 are detected as complex"""
    html = '<table><tr><td colspan="2">Merged</td></tr><tr><td>A</td><td>B</td></tr></table>'
    assert _is_complex_table(html) == True, "Table with colspan=2 should be complex"


def test_complex_table_with_rowspan():
    """Test that tables with rowspan > 1 are detected as complex"""
    html = '<table><tr><td rowspan="3">Merged</td><td>A</td></tr><tr><td>B</td></tr></table>'
    assert _is_complex_table(html) == True, "Table with rowspan=3 should be complex"


def test_simple_table_no_merge():
    """Test that tables without colspan/rowspan are detected as simple"""
    html = '<table><tr><td>A</td><td>B</td></tr><tr><td>C</td><td>D</td></tr></table>'
    assert _is_complex_table(html) == False, "Table without merge should be simple"


def test_simple_table_with_colspan_1():
    """Test that tables with colspan=1 are detected as simple"""
    html = '<table><tr><td colspan="1">A</td><td>B</td></tr></table>'
    assert _is_complex_table(html) == False, "Table with colspan=1 should be simple"


def test_simple_table_with_rowspan_1():
    """Test that tables with rowspan=1 are detected as simple"""
    html = '<table><tr><td rowspan="1">A</td><td>B</td></tr></table>'
    assert _is_complex_table(html) == False, "Table with rowspan=1 should be simple"


def test_generate_block_content_complex_table_outputs_html():
    """Test that complex tables output HTML format (Requirement 3.1, 3.4)"""
    complex_html = '<table><tr><td colspan="2">Merged</td></tr><tr><td>A</td><td>B</td></tr></table>'
    res = {'html': complex_html}
    content = _generate_block_content('table', res)
    
    # Should contain the original HTML
    assert '<table>' in content, "Complex table should output HTML"
    assert 'colspan="2"' in content, "Complex table should preserve colspan attribute"
    assert '|' not in content or '<table>' in content, "Complex table should not be converted to Markdown"


def test_generate_block_content_simple_table_outputs_markdown():
    """Test that simple tables output Markdown format (Requirement 3.5)"""
    simple_html = '<table><tr><th>Header1</th><th>Header2</th></tr><tr><td>A</td><td>B</td></tr></table>'
    res = {'html': simple_html}
    content = _generate_block_content('table', res)
    
    # Should contain Markdown table format
    assert '|' in content, "Simple table should output Markdown with pipe characters"
    assert '<table>' not in content, "Simple table should not contain HTML table tag"
    assert '---' in content, "Simple table should have Markdown separator"


def test_generate_block_content_table_without_html():
    """Test that tables without HTML return placeholder"""
    res = "Some text"
    content = _generate_block_content('table', res)
    assert content == "[表格]", "Table without HTML should return placeholder"


def test_generate_block_content_empty_html():
    """Test that empty HTML returns appropriate placeholder"""
    res = {'html': ''}
    content = _generate_block_content('table', res)
    assert "[空表格]" in content or "[表格]" in content, "Empty HTML should return placeholder"


if __name__ == '__main__':
    print("Running Task 5.2 verification tests...")
    
    test_complex_table_with_colspan()
    print("✓ test_complex_table_with_colspan passed")
    
    test_complex_table_with_rowspan()
    print("✓ test_complex_table_with_rowspan passed")
    
    test_simple_table_no_merge()
    print("✓ test_simple_table_no_merge passed")
    
    test_simple_table_with_colspan_1()
    print("✓ test_simple_table_with_colspan_1 passed")
    
    test_simple_table_with_rowspan_1()
    print("✓ test_simple_table_with_rowspan_1 passed")
    
    test_generate_block_content_complex_table_outputs_html()
    print("✓ test_generate_block_content_complex_table_outputs_html passed")
    
    test_generate_block_content_simple_table_outputs_markdown()
    print("✓ test_generate_block_content_simple_table_outputs_markdown passed")
    
    test_generate_block_content_table_without_html()
    print("✓ test_generate_block_content_table_without_html passed")
    
    test_generate_block_content_empty_html()
    print("✓ test_generate_block_content_empty_html passed")
    
    print("\n✅ All Task 5.2 verification tests passed!")
