"""
Example of an optimisation experiment. Implemented procedure is explained at
https://en.wikipedia.org/wiki/Random_optimization
"""
import high_dimensional_sampling as hds
import numpy as np

from numpy.random import uniform

OPENOPT = SCIPY = True

try:
    from openopt import NLP
except ImportError:
    OPENOPT = False

try:
    from scipy.optimize import minimize
except ImportError:
    SCIPY = False

SCIPY_LOCAL_SOLVERS = ['Nelder-Mead', 'Powell', 'L-BFGS-B', 'TNC', 'SLSQP']
OPENOPT_LOCAL_SOLVERS = [
    'bobyqa', 'ptn', 'slmvm2', 'ralg', 'mma', 'auglag', 'sqlcp'
]


class Ampgo(hds.Procedure):
    def __init__(self, n_initial=10, n_sample=10):
        self.store_parameters = ['n_initial', 'n_sample']
        self.n_initial = n_initial
        self.n_sample = n_sample
        self.reset()

    def __call__(self, function):
        if self.current_position is None:
            # Initial sampling
            self.current_position = self.get_initial_position(
                function.get_ranges(), self.n_initial)
        bounds = function.get_ranges()
        self.function = function

        # Hyper-parameter set empirically
        tolfun = 1e-6

        xf, yf, fun_evals, msg, tt = self.AMPGO(self.evaluator,
                                                self.current_position,
                                                args=(),
                                                local='L-BFGS-B',
                                                bounds=bounds,
                                                maxfunevals=20000,
                                                totaliter=2000,
                                                maxiter=5,
                                                eps1=0.02,
                                                eps2=0.01,
                                                tabulistsize=5,
                                                tabustrategy='farthest',
                                                fmin=0,
                                                disp=1,
                                                glbtol=tolfun)

        # Added for debugging
        print(xf, yf, fun_evals, msg, tt)
        xf = xf.reshape(1, -1)
        yf = yf.reshape(-1, 1)
        return (xf, yf)

    def AMPGO(self,
              objfun,
              x0,
              args=(),
              local='L-BFGS-B',
              local_opts=None,
              bounds=None,
              maxfunevals=None,
              totaliter=20,
              maxiter=5,
              glbtol=1e-5,
              eps1=0.02,
              eps2=0.1,
              tabulistsize=5,
              tabustrategy='farthest',
              fmin=-np.inf,
              disp=None):
        """
     Finds the global minimum of a function using the AMPGO (Adaptive Memory
     Programming for Global Optimization) algorithm.

     :param `objfun`: Function to be optimized, in the form ``f(x, *args)``.
     :type `objfun`: callable
     :param `args`: Additional arguments passed to `objfun`.
     :type `args`: tuple
     :param `local`: The local minimization method (e.g. ``"L-BFGS-B"``). It
                     can be one of the available
     `scipy` local solvers or `OpenOpt` solvers.
     :type `local`: string
     :param `bounds`: A list of tuples specifying the lower and upper bound for
                      each independent variable [(`xl0`, `xu0`),
                      (`xl1`, `xu1`), ...]
     :type `bounds`: list
     :param `maxfunevals`: The maximum number of function evaluations allowed.
     :type `maxfunevals`: integer
     :param `totaliter`: The maximum number of global iterations allowed.
     :type `totaliter`: integer
     :param `maxiter`: The maximum number of `Tabu Tunnelling` iterations
                       allowed during each global iteration.
     :type `maxiter`: integer
     :param `glbtol`: The optimization will stop if the absolute difference
                      between the current minimum objective function value and
                      the provided global optimum (`fmin`) is less than
                      `glbtol`.
     :type `glbtol`: float
     :param `eps1`: A constant used to define an aspiration value for the
                    objective function during the Tunnelling phase.
     :type `eps1`: float
     :param `eps2`: Perturbation factor used to move away from the latest local
                    minimum at the start of a Tunnelling phase.
     :type `eps2`: float
     :param `tabulistsize`: The size of the tabu search list (a circular list).
     :type `tabulistsize`: integer
     :param `tabustrategy`: The strategy to use when the size of the tabu list
                            exceeds `tabulistsize`. It can be 'oldest' to drop
                            the oldest point from the tabu list or 'farthest'
                            to drop the element farthest from the last local
                            minimum found.
     :type `tabustrategy`: string
     :param `fmin`: If known, the objective function global optimum value.
     :type `fmin`: float
     :param `disp`: If zero or defaulted, then no output is printed on screen.
                    If a positive number, then status messages are printed.
     :type `disp`: integer

     :returns: A tuple of 5 elements, in the following order:
     1. **best_x** (`array_like`): the estimated position of the global
                                   minimum.
     2. **best_f** (`float`): the value of `objfun` at the minimum.
     3. **evaluations** (`integer`): the number of function evaluations.
     4. **msg** (`string`): a message describes the cause of the termination.
     5. **tunnel_info** (`tuple`): a tuple containing the total number of
                                   Tunnelling phases performed and the
                                   successful ones.
     :rtype: `tuple`
     The detailed implementation of AMPGO is described in the paper
     "Adaptive Memory Programming for Constrained Global Optimization" located
     here:
     http://leeds-faculty.colorado.edu/glover/fred%20pubs/416%20-%20AMP%20(TS)%20for%20Constrained%20Global%20Opt%20w%20Lasdon%20et%20al%20.pdf
     Copyright 2014 Andrea Gavana
     """

        if local not in SCIPY_LOCAL_SOLVERS + OPENOPT_LOCAL_SOLVERS:
            raise Exception('Invalid local solver selected: %s' % local)

        if local in SCIPY_LOCAL_SOLVERS and not SCIPY:
            raise Exception(
                'Solver %s is not available (scipy not installed)'
                % local)

        if local in OPENOPT_LOCAL_SOLVERS and not OPENOPT:
            raise Exception(
                'Solver %s is not available (OpenOpt not installed)'
                % local)

        x0 = np.atleast_1d(x0)
        n = len(x0)

        # rruiz
        bounds = list(bounds)

        if bounds is None:
            bounds = [(None, None)] * n
        if len(bounds) != n:
            raise ValueError('length of x0 != length of bounds')

        low = [0] * n
        up = [0] * n
        for i in range(n):
            if bounds[i] is None:
                l, u = -np.inf, np.inf
            else:
                l, u = bounds[i]
                if l is None:
                    low[i] = -np.inf
                else:
                    low[i] = l
                if u is None:
                    up[i] = np.inf
                else:
                    up[i] = u

        if maxfunevals is None:
            maxfunevals = max(100, 10 * len(x0))

        if tabulistsize < 1:
            raise Exception(
                "tabulistsize (%s) should be an integer greater than zero."
                % tabulistsize)
        if tabustrategy not in ['oldest', 'farthest']:
            raise Exception(
                'tabustrategy (%s) must be one of "oldest" or "farthest"'
                % tabustrategy)

        iprint = 50
        if disp is None or disp <= 0:
            disp = 0
            iprint = -1

        low = np.asarray(low)
        up = np.asarray(up)

        tabulist = []
        best_f = np.inf
        best_x = x0

        global_iter = 0
        all_tunnel = success_tunnel = 0
        evaluations = 0

        if glbtol < 1e-8:
            local_tol = glbtol
        else:
            local_tol = 1e-8

        while 1:

            if disp > 0:
                print('\n')
                print('=' * 72)
                print('Starting MINIMIZATION Phase %-3d' % (global_iter + 1))
                print('=' * 72)

            if local in OPENOPT_LOCAL_SOLVERS:
                problem = NLP(objfun,
                              x0,
                              lb=low,
                              ub=up,
                              maxFunEvals=max(1, maxfunevals),
                              ftol=local_tol,
                              iprint=iprint)
                problem.args = args

                results = problem.solve(local)
                xf, yf, num_fun = results.xf, results.ff, results.evals['f']
            else:
                options = {'maxiter': max(1, maxfunevals), 'disp': disp}
                if local_opts is not None:
                    options.update(local_opts)
                res = minimize(objfun,
                               x0,
                               args=args,
                               method=local,
                               bounds=bounds,
                               tol=local_tol,
                               options=options)
                xf, yf, num_fun = res['x'], res['fun'], res['nfev']

            maxfunevals -= num_fun
            evaluations += num_fun

            if yf < best_f:
                best_f = yf
                best_x = xf

            if disp > 0:
                print('\n\n ==> Reached local minimum: %s\n' % yf)

            if best_f < fmin + glbtol:
                if disp > 0:
                    print('=' * 72)
                return (best_x, best_f, evaluations,
                        'Optimization terminated successfully',
                        (all_tunnel, success_tunnel))
            if maxfunevals <= 0:
                if disp > 0:
                    print('=' * 72)
                return (best_x, best_f, evaluations,
                        'Maximum number of function evaluations exceeded',
                        (all_tunnel, success_tunnel))

            tabulist = self.drop_tabu_points(xf, tabulist, tabulistsize,
                                             tabustrategy)
            tabulist.append(xf)

            i = improve = 0

            while i < maxiter and improve == 0:

                if disp > 0:
                    print('-' * 72)
                    print('Starting TUNNELLING   Phase (%3d-%3d)' %
                          (global_iter + 1, i + 1))
                    print('-' * 72)

                all_tunnel += 1

                r = np.random.uniform(-1.0, 1.0, size=(n, ))
                beta = eps2 * np.linalg.norm(xf) / np.linalg.norm(r)

                if np.abs(beta) < 1e-8:
                    beta = eps2

                x0 = xf + beta * r

                x0 = np.where(x0 < low, low, x0)
                x0 = np.where(x0 > up, up, x0)

                aspiration = best_f - eps1 * (1.0 + np.abs(best_f))

                tunnel_args = tuple([objfun, aspiration, tabulist] +
                                    list(args))

                if local in OPENOPT_LOCAL_SOLVERS:
                    problem = NLP(self.tunnel,
                                  x0,
                                  lb=low,
                                  ub=up,
                                  maxFunEvals=max(1, maxfunevals),
                                  ftol=local_tol,
                                  iprint=iprint)
                    problem.args = tunnel_args

                    results = problem.solve(local)
                    xf, yf, num_fun = results.xf, results.ff, results.evals[
                        'f']
                else:
                    options = {'maxiter': max(1, maxfunevals), 'disp': disp}
                    if local_opts is not None:
                        options.update(local_opts)

                    res = minimize(self.tunnel,
                                   x0,
                                   args=tunnel_args,
                                   method=local,
                                   bounds=bounds,
                                   tol=local_tol,
                                   options=options)
                    xf, yf, num_fun = res['x'], res['fun'], res['nfev']

                maxfunevals -= num_fun
                evaluations += num_fun

                yf = self.inverse_tunnel(xf, yf, aspiration, tabulist)

                if yf <= best_f + glbtol:
                    oldf = best_f
                    best_f = yf
                    best_x = xf
                    improve = 1
                    success_tunnel += 1

                    if disp > 0:
                        print(
                            ('\n\n ==> Successful tunnelling phase.'
                             'Reached local minimum: %s < %s\n')
                            % (yf, oldf))

                if best_f < fmin + glbtol:
                    return (best_x, best_f, evaluations,
                            'Optimization terminated successfully',
                            (all_tunnel, success_tunnel))

                i += 1

                if maxfunevals <= 0:
                    return (best_x, best_f, evaluations,
                            'Maximum number of function evaluations exceeded',
                            (all_tunnel, success_tunnel))

                tabulist = self.drop_tabu_points(xf, tabulist, tabulistsize,
                                                 tabustrategy)
                tabulist.append(xf)

            if disp > 0:
                print('=' * 72)

            global_iter += 1
            x0 = xf.copy()

            if global_iter >= totaliter:
                return (best_x, best_f, evaluations,
                        'Maximum number of global iterations exceeded',
                        (all_tunnel, success_tunnel))

            if best_f < fmin + glbtol:
                return (best_x, best_f, evaluations,
                        'Optimization terminated successfully',
                        (all_tunnel, success_tunnel))

    def drop_tabu_points(self, xf, tabulist, tabulistsize, tabustrategy):

        if len(tabulist) < tabulistsize:
            return tabulist

        if tabustrategy == 'oldest':
            tabulist.pop(0)
        else:
            distance = np.sqrt(np.sum((tabulist - xf)**2, axis=1))
            index = np.argmax(distance)
            tabulist.pop(index)

        return tabulist

    def tunnel(self, x0, objfun, aspiration, tabulist, *args):

        fun_args = tuple()

        numerator = (objfun(x0, *fun_args) - aspiration)**2
        denominator = 1.0

        for tabu in tabulist:
            denominator = denominator * np.sqrt(np.sum((x0 - tabu)**2))

        ytf = numerator / denominator

        return ytf

    def inverse_tunnel(self, xtf, ytf, aspiration, tabulist):

        denominator = 1.0

        for tabu in tabulist:
            denominator = denominator * np.sqrt(np.sum((xtf - tabu)**2))

        yf = aspiration + np.sqrt(ytf * denominator)
        return yf

    def get_initial_position(self, ranges, n_sample_initial):
        x = [uniform(left, right) for left, right in ranges]
        return x

    def get_point(self, ranges, stdev=0.01, n_sample=1):
        cov = np.identity(len(ranges)) * stdev
        return np.random.multivariate_normal(self.current_position[0], cov,
                                             n_sample)

    def evaluator(self, x, *args):
        x = np.expand_dims(x, axis=0)
        y = self.function(x)
        return y[0][0]

    def reset(self):
        self.current_position = None
        self.current_value = None

    def is_finished(self):
        return False

    def check_testfunction(self, function):
        return True
