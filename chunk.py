def decouper_en_chunks(texte, taille_chunk=500, chevauchement=50):
    """
    Découpe un texte en morceaux de taille fixe, avec un léger chevauchement
    entre chaque morceau pour ne pas couper une idée importante en plein milieu.
    """
    chunks = []
    debut = 0

    while debut < len(texte):
        fin = debut + taille_chunk
        chunk = texte[debut:fin]
        chunks.append(chunk)
        debut += taille_chunk - chevauchement  # on recule un peu avant le prochain chunk

    return chunks


if __name__ == "__main__":
    from text_extract import extraire_texte_pdf

    texte = extraire_texte_pdf("factures/facture_test.pdf")
    chunks = decouper_en_chunks(texte)

    print(f"Nombre de chunks créés : {len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(f"\n--- Chunk {i+1} ({len(chunk)} caractères) ---")
        print(chunk)