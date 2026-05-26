:- dynamic symptom/1.

% =========================
% WEIGHTS
% =========================

weight(fever, 5).
weight(chills, 30).
weight(headache, 20).
weight(cough, 10).
weight(tiredness, 10).
weight(sore_throat, 5).
weight(body_pain, 25).
weight(running_nose, 20).
weight(sweating, 30).
weight(loss_of_taste, 35).
weight(sneezing, 25).

% =========================
% DISEASE SYMPTOMS
% =========================

disease_symptom(malaria, fever).
disease_symptom(malaria, chills).
disease_symptom(malaria, headache).
disease_symptom(malaria, sweating).

disease_symptom(flu, fever).
disease_symptom(flu, cough).
disease_symptom(flu, body_pain).
disease_symptom(flu, sneezing).

disease_symptom(covid19, fever).
disease_symptom(covid19, cough).
disease_symptom(covid19, tiredness).
disease_symptom(covid19, sore_throat).
disease_symptom(covid19, loss_of_taste).

disease_symptom(common_cold, running_nose).
disease_symptom(common_cold, cough).
disease_symptom(common_cold, sore_throat).