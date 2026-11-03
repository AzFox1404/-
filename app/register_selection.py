"""Position selection independent of Tk and Office."""
def following_rows(values,active,count):
    rows=sorted({int(k.split('_')[0][3:]) for k in values if k.startswith('row')})
    # Both a new construction section and a document-group heading are barriers.
    headings=[int(k[len(prefix):]) for k in values for prefix in ('part','group')
              if k.startswith(prefix) and k[len(prefix):].isdigit()]
    stop=min((r for r in headings if r>active),default=float('inf'))
    available=[];previous=active
    for r in rows:
        if r<=active:continue
        # Unknown Word headings need not expose a part/group field. Never jump
        # across a non-position row, which can be such a heading or the totals.
        if r>=stop or r!=previous+1:break
        available.append(r);previous=r
    return available[:count],len(available)
