# Flux d'Interaction du Système

Ce document détaille les séquences d'interaction et les états du flux de données du Maillage de Suggestion de Documents Word.

## 1. Diagramme de Séquence : Cycle de Traitement du Document

Ce diagramme montre l'interaction étape par étape entre les composants au fil du temps, du téléchargement à la livraison finale des suggestions.

```mermaid
sequenceDiagram
    autonumber
    participant U as Utilisateur / Complément Word<br/>(C)
    participant I as Service d'Ingestion<br/>(P)
    participant R as Flux Redis<br/>(Bus)
    participant C as Agent Coordinateur<br/>(C & P)
    participant G as Agent Grammaire<br/>(C & P)
    participant T as Agent Ton<br/>(C & P)
    participant A as Agent Agrégateur<br/>(C & P)

    %% Phase d'Entrée
    rect rgb(240, 248, 255)
    note right of U: Phase d'Entrée
    U->>I: Télécharger fichier .docx
    activate I
    I->>I: Analyser structure .docx
    I->>I: Diviser en morceaux (C1, C2...)
    I->>R: XADD doc.review.tasks (Données du morceau)
    deactivate I
    end

    %% Phase de Coordination
    rect rgb(255, 250, 205)
    note right of R: Coordination
    R-->>C: Nouveau Message (Données du morceau)
    activate C
    C->>C: Analyser Requête
    par Distribution des Tâches
        C->>R: XADD doc.review.grammar
        C->>R: XADD doc.review.tone
    end
    C->>R: XACK doc.review.tasks
    deactivate C
    end

    %% Phase de Traitement Spécialisé
    rect rgb(255, 228, 225)
    note right of R: Traitement Spécialisé
    par Traitement Parallèle
        R-->>G: Lire doc.review.grammar
        activate G
        G->>G: Vérifier Règles Grammaire
        G->>R: XADD doc.suggestions.grammar
        G->>R: XACK doc.review.grammar
        deactivate G
    and
        R-->>T: Lire doc.review.tone
        activate T
        T->>T: Vérifier Cohérence Ton
        T->>R: XADD doc.suggestions.tone
        T->>R: XACK doc.review.tone
        deactivate T
    end
    end

    %% Agrégation & Livraison
    rect rgb(240, 255, 240)
    note right of A: Agrégation & Sortie
    loop Collecte des Résultats
        R-->>A: Lire doc.suggestions.*
        activate A
        A->>A: Tamponner & Grouper par DocID
    end
    
    A->>A: Fusionner Suggestions
    A->>R: XADD doc.review.summary
    deactivate A

    R-->>U: Lire Résumé Final
    U->>U: Afficher Suggestions
    end
```

## 2. Explication de l'Interaction

### Phase 1 : Entrée
L'**Utilisateur** (Producteur de fichier) télécharge un fichier. Le **Service d'Ingestion** (Producteur de Tâches) agit comme la frontière, convertissant le fichier binaire `.docx` en tâches discrètes basées sur du texte stockées dans **Redis**. Il *produit* des messages dans le flux `doc.review.tasks`.

### Phase 2 : Coordination
L'**Agent Coordinateur** est à la fois **Consommateur** (il lit les tâches brutes) et **Producteur** (il *produit* des demandes de revue spécifiques). Il décide *ce qui* doit être fait. Si l'utilisateur a uniquement demandé une vérification grammaticale, il ne *produira* des messages que vers `doc.review.grammar`.

### Phase 3 : Traitement Spécialisé
Les **agents Grammaire** et **Ton** (Consommateurs & Producteurs) travaillent en parallèle. Ils *consomment* leurs tâches spécifiques depuis Redis, effectuent un traitement IA intensif, et *produisent* leurs conclusions (suggestions) vers un modèle commun `doc.suggestions.*`.

### Phase 4 : Agrégation
L'**Agent Agrégateur** (Consommateur Final & Producteur de Résumé) *consomme* tous les canaux de suggestion. Il attend d'avoir reçu les retours de tous les agents attendus pour un morceau spécifique. Il fusionne ensuite ces objets JSON séparés en un résultat unique et cohérent, et *produit* le rapport final dans le flux de résumé pour que l'**Utilisateur** (Consommateur Final) puisse le lire.
