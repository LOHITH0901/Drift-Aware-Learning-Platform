class BKTTracker:
    def __init__(self, p_init=0.5, p_learn=0.1, p_guess=0.2, p_slip=0.1):
        self.p_init = p_init
        self.p_learn = p_learn
        self.p_guess = p_guess
        self.p_slip = p_slip

    def update_mastery(self, current_mastery: float, is_correct: bool) -> float:
        """
        Updates the mastery probability based on the observation.
        """
        if is_correct:
            # P(L|Correct) = [P(L)(1-P(S))] / [P(L)(1-P(S)) + (1-P(L))P(G)]
            numerator = current_mastery * (1 - self.p_slip)
            denominator = numerator + (1 - current_mastery) * self.p_guess
        else:
            # P(L|Incorrect) = [P(L)P(S)] / [P(L)P(S) + (1-P(L))(1-P(G))]
            numerator = current_mastery * self.p_slip
            denominator = numerator + (1 - current_mastery) * (1 - self.p_guess)
        
        p_l_given_obs = numerator / denominator if denominator > 0 else 0.0

        # P(L_next) = P(L|Obs) + (1 - P(L|Obs)) * P(T)
        next_mastery = p_l_given_obs + (1 - p_l_given_obs) * self.p_learn
        
        return next_mastery

    def predict_correctness(self, current_mastery: float) -> float:
        """
        Predicts the probability of a correct answer given the current mastery.
        P(Correct) = P(L)(1-P(S)) + (1-P(L))P(G)
        """
        return current_mastery * (1 - self.p_slip) + (1 - current_mastery) * self.p_guess
