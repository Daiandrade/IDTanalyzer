# Script para modificar idt_engine.py
with open("idt_engine.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Encontrar linha com "# Calcular total de municípios únicos"
new_lines = []
i = 0
replaced = False

while i < len(lines):
    line = lines[i]
    
    # Detectar início da seção a ser substituída
    if "# Calcular total de municípios únicos" in line and not replaced:
        # Adicionar novo código
        new_lines.append("    # Calcular totais baseados em LINHAS (volumetria)\n")
        new_lines.append("    total_linhas = len(detail)  # Total de linhas processadas\n")
        new_lines.append('    linhas_atendidas = sum(1 for d in detail if d["Status"] == "Atendido")\n')
        new_lines.append('    linhas_nao_atendidas = sum(1 for d in detail if d["Status"] == "Não Atendido")\n')
        new_lines.append('    linhas_invalidas = sum(1 for d in detail if d["Status"] == "Município Não Válido")\n')
        new_lines.append("\n")
        new_lines.append("    # Calcular totais baseados em MUNICÍPIOS ÚNICOS (para informação)\n")
        new_lines.append("    total_municipios_unicos = len(in_scope_unique) + len(out_of_scope_unique) + len(invalid_unique)\n")
        
        # Pular 2 linhas antigas
        i += 3
        replaced = True
        continue
    
    # Substituir "if total_municipios == 0:" por "if total_linhas == 0:"
    if "if total_municipios == 0:" in line and replaced:
        new_lines.append("    # Se não houver nenhuma linha, não analisa\n")
        new_lines.append("    if total_linhas == 0:\n")
        i += 2
        continue
    
    # Ajustar return vazio
    if '"total": 0,' in line and '"in_scope": []' in lines[i+1] and replaced and not '"total_linhas"' in line:
        new_lines.append('            "total": 0,\n')
        new_lines.append('            "total_linhas": 0,\n')
        i += 1
        continue
    
    # Adicionar novos campos no return vazio (antes de score)
    if '"score": None,' in line and '"detail": [],' in lines[i+1] and not '"linhas_atendidas"' in ''.join(new_lines[-5:]):
        new_lines.append('            "linhas_atendidas": 0,\n')
        new_lines.append('            "linhas_nao_atendidas": 0,\n')
        new_lines.append('            "linhas_invalidas": 0,\n')
        new_lines.append(line)
        i += 1
        continue
    
    # Substituir cálculo de score
    if "# Calcular score: % de municípios ATENDIDOS" in line and replaced:
        new_lines.append("    # NOVO: Calcular score baseado em LINHAS (volumetria), não municípios únicos\n")
        new_lines.append("    # Score = (Linhas Atendidas / Total de Linhas) × 100\n")
        new_lines.append("    score = round((linhas_atendidas / total_linhas) * 100.0, 2)\n")
        i += 3
        continue
    
    # Substituir return final
    if "    return {" in line and '"total": total_municipios,' in lines[i+1] and replaced:
        new_lines.append("    return {\n")
        new_lines.append("        # Totais baseados em LINHAS (volumetria)\n")
        new_lines.append('        "total_linhas": total_linhas,\n')
        new_lines.append('        "linhas_atendidas": linhas_atendidas,\n')
        new_lines.append('        "linhas_nao_atendidas": linhas_nao_atendidas,\n')
        new_lines.append('        "linhas_invalidas": linhas_invalidas,\n')
        new_lines.append("\n")
        new_lines.append("        # Totais baseados em MUNICÍPIOS ÚNICOS (para listas)\n")
        new_lines.append('        "total": total_municipios_unicos,\n')
        
        # Pular até encontrar "score": score
        i += 2
        while i < len(lines) and '"score": score,' not in lines[i]:
            if '"in_scope":' in lines[i] or '"out_of_scope":' in lines[i] or '"invalid":' in lines[i] or '"covered":' in lines[i] or '"not_covered":' in lines[i] or '"invalid_count":' in lines[i]:
                new_lines.append(lines[i])
            i += 1
        
        new_lines.append("\n")
        new_lines.append("        # Score baseado em LINHAS (volumetria)\n")
        new_lines.append('        "score": score,\n')
        new_lines.append("\n")
        new_lines.append("        # Detalhe de TODAS as linhas\n")
        new_lines.append('        "detail": detail,\n')
        new_lines.append("    }\n")
        
        # Pular até o final do return
        while i < len(lines) and "    }" not in lines[i]:
            i += 1
        i += 1
        continue
    
    new_lines.append(line)
    i += 1

# Salvar
with open("idt_engine.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Modificado com sucesso!")
