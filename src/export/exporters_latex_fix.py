# LaTeX exporter fix - replace lines 304-341 in exporters.py

            # Begin table
            f.write(r"\begin{table}[htbp]" + "\n")
            f.write(r"\centering" + "\n")
            if caption:
                f.write(r"\caption{" + caption + "}\n")
            if label:
                f.write(r"\label{" + label + "}\n")

            # Begin tabular
            col_spec = 'l' * num_cols
            f.write(r"\begin{tabular}{" + col_spec + "}\n")
            f.write(r"\toprule" + "\n")

            # Write headers
            header_line = ' & '.join([sanitize_latex(str(h)) for h in headers])
            f.write(header_line + r" \\" + "\n")
            f.write(r"\midrule" + "\n")

            # Write data rows
            for row_data in export_data:
                row_values = []
                for header in headers:
                    value = row_data.get(header, '')
                    if isinstance(value, float):
                        formatted = f"{value:.{precision}f}"
                    elif isinstance(value, int):
                        formatted = format_number(value)
                    else:
                        formatted = str(value)
                    row_values.append(sanitize_latex(formatted))

                row_line = ' & '.join(row_values)
                f.write(row_line + r" \\" + "\n")

            # End tabular
            f.write(r"\bottomrule" + "\n")
            f.write(r"\end{tabular}" + "\n")
            f.write(r"\end{table}" + "\n")
