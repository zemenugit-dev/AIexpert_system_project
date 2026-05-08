:- dynamic symptom/1.

% =========================
% WEIGHTS (GLOBAL SYMPTOM IMPORTANCE)
% =========================
weight(fever, 30).
weight(chills, 30).
weight(headache, 20).
weight(cough, 40).
weight(tiredness, 40).
weight(sore_throat, 25).
weight(body_pain, 25).
weight(running_nose, 20).

% =========================
% DISEASE SYMPTOMS
% =========================

disease_symptom(malaria, fever).
disease_symptom(malaria, chills).
disease_symptom(malaria, headache).

disease_symptom(flu, fever).
disease_symptom(flu, cough).
disease_symptom(flu, body_pain).

disease_symptom(covid19, fever).
disease_symptom(covid19, cough).
disease_symptom(covid19, tiredness).
disease_symptom(covid19, sore_throat).

disease_symptom(common_cold, running_nose).
disease_symptom(common_cold, cough).
disease_symptom(common_cold, sore_throat).

% =========================
% SCORING FUNCTION
% =========================
disease_score(Disease, Score) :-
    findall(W,
        (
            disease_symptom(Disease, S),
            symptom(S),
            weight(S, W)
        ),
        L),
    sum_list(L, Score).