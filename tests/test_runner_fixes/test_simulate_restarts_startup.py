"""FIX 15: a restart fires the submission check at startup, and restores the
learned caches before the loop generates anything.

The loaders now live in `runner.explore_loop.startup`, so that is the module the
tests patch; `loop._startup_checks` stays the entry point under test."""


def test_startup_fires_the_submission_check(monkeypatch):
    """A restart must drain the check queue, not postpone it.

    The periodic trigger counts completed batches from process start; with
    restarts every few minutes it never reaches its interval, which starved
    the queue for hours today. The startup fire is what makes a restart
    validate the top alphas instead of postponing them.
    """
    import runner.explore_loop.loop as loopmod
    import runner.explore_loop.startup as startupmod

    fired = []
    monkeypatch.setattr(startupmod, "start_background_check", lambda: fired.append(True))

    loopmod._startup_checks(object(), None)
    assert fired == [True]


def test_startup_fires_the_check_even_when_weight_refresh_fails(monkeypatch):
    import runner.explore_loop.loop as loopmod
    import runner.explore_loop.startup as startupmod

    fired = []

    def boom(*a, **k):
        raise RuntimeError("db busy")

    monkeypatch.setattr(startupmod, "start_background_check", lambda: fired.append(True))
    monkeypatch.setattr(startupmod, "load_diversity_weights", boom)

    loopmod._startup_checks(object(), None)
    assert fired == [True]


def test_startup_loads_the_learned_weight_caches(monkeypatch):
    """Both caches are empty in a fresh process and the maintenance refresh is
    50 alphas away, so without this the F3 feedback loop and the correlation
    weight are silently off after every restart. Measured 2026-10-07: loaded at
    07:17, restarted at 07:41, generation blind until the next maintenance.
    """
    import runner.explore_loop.loop as loopmod
    import runner.explore_loop.startup as startupmod

    loaded = []
    monkeypatch.setattr(startupmod, "start_background_check", lambda: None)
    monkeypatch.setattr(startupmod.cell_priors, "load_priors", lambda conn: loaded.append("cell"))
    monkeypatch.setattr(startupmod, "load_corr_prior", lambda conn: loaded.append("corr"))

    loopmod._startup_checks(object(), None)
    assert loaded == ["cell", "corr"]
