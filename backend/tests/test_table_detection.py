"""
Property-based tests for complex table detection and HTML preservation

Feature: workbench-v2-optimization, Property 4: 复杂表格检测与 HTML 保留
**Validates: Requirements 3.1, 3.3, 3.4**
"""
import pytest
from hypothesis import given, strategies as st, settings
from backend.api.workbench_routes import _is_complex_table, _generate_block_content


@st.composite
def simple_cell_content_strategy(draw):
    """Generate simple cell content"""
    return draw(st.text(
        min_size=1,
        max_size=20,
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters=' '
        )
    ))


@st.composite
def complex_table_html_strategy(draw):
    """Generate HTML table with colspan > 1 or rowspan > 1"""
    rows = draw(st.integers(min_value=2, max_value=5))
    cols = draw(st.integers(min_value=2, max_value=5))
    merge_row = draw(st.integers(min_value=0, max_value=rows - 1))
    merge_col = draw(st.integers(min_value=0, max_value=cols - 1))
    merge_type = draw(st.sampled_from(['colspan', 'rowspan', 'both']))
    max_colspan = cols - merge_col
    max_rowspan = rows - merge_row
    
    if merge_type == 'colspan':
        colspan = draw(st.integers(min_value=2, max_value=max(2, max_colspan)))
        rowspan = 1
    elif merge_type == 'rowspan':
        colspan = 1
        rowspan = draw(st.integers(min_value=2, max_value=max(2, max_rowspan)))
    else:
        colspan = draw(st.integers(min_value=2, max_value=max(2, max_colspan)))
        rowspan = draw(st.integers(min_value=2, max_value=max(2, max_rowspan)))
    
    html_parts = ['<table>']
    covered_cells = set()
    for r in range(merge_row, min(merge_row + rowspan, rows)):
        for c in range(merge_col, min(merge_col + colspan, cols)):
            if r != merge_row or c != merge_col:
                covered_cells.add((r, c))
    
    for row_idx in range(rows):
        html_parts.append('<tr>')
        for col_idx in range(cols):
            if (row_idx, col_idx) in covered_cells:
                continue
            cell_content = draw(simple_cell_content_strategy())
            if row_idx == merge_row and col_idx == merge_col:
                attrs = []
                if colspan > 1:
                    attrs.append(f'colspan="{colspan}"')
                if rowspan > 1:
                    attrs.append(f'rowspan="{rowspan}"')
                attr_str = ' ' + ' '.join(attrs) if attrs else ''
                html_parts.append(f'<td{attr_str}>{cell_content}</td>')
            else:
                html_parts.append(f'<td>{cell_content}</td>')
        html_parts.append('</tr>')
    html_parts.append('</table>')
    return '\n'.join(html_parts)


@st.composite
def simple_table_html_strategy(draw):
    """Generate HTML table without colspan/rowspan > 1"""
    rows = draw(st.integers(min_value=1, max_value=5))
    cols = draw(st.integers(min_value=1, max_value=5))
    include_explicit_attrs = draw(st.booleans())
    html_parts = ['<table>']
    
    for row_idx in range(rows):
        html_parts.append('<tr>')
        for col_idx in range(cols):
            cell_content = draw(simple_cell_content_strategy())
            if include_explicit_attrs:
                attr_type = draw(st.sampled_from(['none', 'colspan', 'rowspan', 'both']))
                if attr_type == 'colspan':
                    html_parts.append(f'<td colspan="1">{cell_content}</td>')
                elif attr_type == 'rowspan':
                    html_parts.append(f'<td rowspan="1">{cell_content}</td>')
                elif attr_type == 'both':
                    html_parts.append(f'<td colspan="1" rowspan="1">{cell_content}</td>')
                else:
                    html_parts.append(f'<td>{cell_content}</td>')
            else:
                html_parts.append(f'<td>{cell_content}</td>')
        html_parts.append('</tr>')
    html_parts.append('</table>')
    return '\n'.join(html_parts)


class TestComplexTableDetectionProperties:
    """
    Property-based tests for complex table detection
    
    Feature: workbench-v2-optimization, Property 4: 复杂表格检测与 HTML 保留
    **Validates: Requirements 3.1, 3.3, 3.4**
    """
    
    @settings(max_examples=100, deadline=None)
    @given(html_table=complex_table_html_strategy())
    def test_property_complex_table_detected(self, html_table):
        """Property 4.1: Complex tables should be detected"""
        result = _is_complex_table(html_table)
        assert result is True, f'Complex table should be detected. HTML: {html_table[:200]}...'
    
    @settings(max_examples=100, deadline=None)
    @given(html_table=simple_table_html_strategy())
    def test_property_simple_table_not_detected_as_complex(self, html_table):
        """Property 4.2: Simple tables should NOT be detected as complex"""
        result = _is_complex_table(html_table)
        assert result is False, f'Simple table should NOT be complex. HTML: {html_table[:200]}...'
    
    @settings(max_examples=100, deadline=None)
    @given(html_table=complex_table_html_strategy())
    def test_property_complex_table_preserves_html(self, html_table):
        """Property 4.3: Complex tables should output HTML format"""
        res = {'html': html_table}
        result = _generate_block_content('table', res)
        assert '<table>' in result.lower(), 'Output should contain HTML table tag'
        assert '</table>' in result.lower(), 'Output should contain closing HTML table tag'
    
    @settings(max_examples=100, deadline=None)
    @given(colspan=st.integers(min_value=2, max_value=10))
    def test_property_colspan_only_detected(self, colspan):
        """Property 4.5: Tables with colspan > 1 should be complex"""
        html = f'<table><tr><td colspan="{colspan}">Merged</td></tr><tr><td>Cell</td></tr></table>'
        result = _is_complex_table(html)
        assert result is True, f'Table with colspan={colspan} should be complex'
    
    @settings(max_examples=100, deadline=None)
    @given(rowspan=st.integers(min_value=2, max_value=10))
    def test_property_rowspan_only_detected(self, rowspan):
        """Property 4.6: Tables with rowspan > 1 should be complex"""
        html = f'<table><tr><td rowspan="{rowspan}">Merged</td><td>Cell</td></tr><tr><td>Cell</td></tr></table>'
        result = _is_complex_table(html)
        assert result is True, f'Table with rowspan={rowspan} should be complex'
    
    @settings(max_examples=100, deadline=None)
    @given(colspan=st.integers(min_value=2, max_value=5), rowspan=st.integers(min_value=2, max_value=5))
    def test_property_both_colspan_rowspan_detected(self, colspan, rowspan):
        """Property 4.7: Tables with both colspan and rowspan > 1 should be complex"""
        html = f'<table><tr><td colspan="{colspan}" rowspan="{rowspan}">Merged</td><td>Cell</td></tr><tr><td>Cell</td></tr></table>'
        result = _is_complex_table(html)
        assert result is True, f'Table with colspan={colspan} and rowspan={rowspan} should be complex'


class TestComplexTableEdgeCases:
    """Edge case tests for complex table detection"""
    
    def test_empty_html_returns_false(self):
        """Empty HTML should return False"""
        assert _is_complex_table('') is False
        assert _is_complex_table(None) is False
    
    def test_no_table_returns_false(self):
        """HTML without table should return False"""
        assert _is_complex_table('<div>No table here</div>') is False
    
    def test_malformed_html_handled_gracefully(self):
        """Malformed HTML should be handled gracefully"""
        result = _is_complex_table('<table><tr><td colspan="2">Test')
        assert isinstance(result, bool)
    
    def test_invalid_colspan_value_handled(self):
        """Invalid colspan values should be handled gracefully"""
        html = '<table><tr><td colspan="invalid">Test</td></tr></table>'
        result = _is_complex_table(html)
        assert isinstance(result, bool)
    
    def test_zero_span_values_not_complex(self):
        """Zero span values should not be considered complex"""
        html = '<table><tr><td colspan="0">Test</td></tr></table>'
        result = _is_complex_table(html)
        assert result is False
    
    def test_generate_block_content_non_table_type(self):
        """Non-table types should not be affected"""
        result = _generate_block_content('text', 'Some text content')
        assert 'Some text content' in result
    
    def test_generate_block_content_table_without_html_key(self):
        """Table without html key should return placeholder"""
        result = _generate_block_content('table', 'plain text')
        assert '[表格]' in result
