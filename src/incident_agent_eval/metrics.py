from time import perf_counter


class Timer:
    def __enter__(self) -> "Timer":
        self.started = perf_counter()
        return self

    def __exit__(self, *_args: object) -> None:
        self.completed = perf_counter()
        self.elapsed_ms = int((self.completed - self.started) * 1000)
