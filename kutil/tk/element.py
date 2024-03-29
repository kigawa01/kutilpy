import abc
import threading
import tkinter
import traceback
from abc import ABC
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from queue import Queue
from tkinter import ttk
from typing import Optional, Any
from typing import Self, Callable, override


class ElementBase[T](ABC):
    element: T

    def __init__(self, element: T):
        self.element = element


class MiscBase[T: tkinter.Misc](
    ElementBase[T],
    ABC
):

    def __init__(self, element: T):
        super().__init__(element)
        self.bind("<FocusIn>", self._on_focus)
        self._on_left_click = list[Callable[[any], any]]()

    def bind(self, sequence: str, func: Callable[[tkinter.Event], object | None]):
        self.element.bind(sequence, func)

    def _on_focus(self, event):
        self.on_focus(event)

    def on_focus(self, event):
        pass

    def on_pre_destroy(self):
        pass

    def add_on_left_click[** ARG](self, func: Callable[ARG, any], *args: ARG) -> Self:
        self.bind("<Button-1>", lambda event: func(*args))
        return self

    def destroy(self):
        self.on_pre_destroy()
        self.element.destroy()

    def after(self, milli_sec: int, func: Callable[[], None]):
        self.element.after(milli_sec, func)


class ElementContainer[T: tkinter.Misc, W: 'WindowBase'](
    MiscBase[T],
    ABC,
):

    def __init__(self, element: T):
        super().__init__(element)

    @abc.abstractmethod
    def window(self) -> W:
        raise NotImplementedError

    def frame[T: FrameBase](self, frame: type[T], *args) -> T:
        return frame(self, *args)

    def button(self, text: str):
        return Button(self, text)

    def entry(self):
        return Entry(self)

    def label(self, text: str):
        return Label(self, text)

    def labelEntry(self, text: str):
        return LabelEntry(self, text)

    def y_scroll_frame[T: FrameBase](self, frame: type[T], *args) -> T:
        canvas = Canvas(self)
        frame_element = canvas.frame(frame, *args)
        canvas.y_scroll()
        canvas.create_window(0, 0, frame_element)
        canvas.pack()
        return frame_element


class GridBase[T: tkinter.Grid](
    ElementBase[T],
    ABC,
):
    def __init__(self, element: T):
        super().__init__(element)

    def grid(self) -> Self:
        self.element.grid_configure()
        return self

    def column_span(self, size: int) -> Self:
        self.element.grid_configure(columnspan=size)
        return self

    def raw(self, index: int) -> Self:
        self.element.grid_configure(row=index)
        return self

    def column(self, index: int) -> Self:
        self.element.grid_configure(column=index)
        return self


class SideType(Enum):
    LEFT = tkinter.LEFT
    TOP = tkinter.TOP
    RIGHT = tkinter.RIGHT
    BOTTOM = tkinter.BOTTOM


class AnchorType(Enum):
    N = tkinter.N
    S = tkinter.S
    W = tkinter.W
    E = tkinter.E


class PackBase[T: tkinter.Pack](
    ElementBase[T],
    ABC,
):

    def __init__(self, element: T):
        super().__init__(element)

    def pack(self) -> Self:
        self.element.pack_configure()
        return self

    def side(self, side: SideType) -> Self:
        self.element.pack_configure(side=side.value)
        return self

    def anchor(self, anchor: AnchorType) -> Self:
        self.element.pack_configure(anchor=anchor.value)
        return self

    def pad(self, margin: int) -> Self:
        self.element.pack_configure(padx=margin, pady=margin)
        return self

    def ipad(self, margin: int) -> Self:
        self.element.pack_configure(ipadx=margin, ipady=margin)
        return self

    def padx(self, left: int, right: int | None = None) -> Self:
        if right is None:
            right = left
        self.element.pack_configure(padx=(left, right))
        return self

    def pady(self, top: int, bottom: int | None = None) -> Self:
        if bottom is None:
            bottom = top
        self.element.pack_configure(pady=(top, bottom))
        return self


class ThreadBase[T: tkinter.Misc](
    MiscBase[T],
    ABC,
):

    def __init__(self, element: T):
        super().__init__(element)
        self.sync_tasks = Queue[Callable[[], any]]()
        self.closed = False
        self.lock = threading.Lock()
        self._sync_task_timer()

    @abc.abstractmethod
    def executor(self) -> ThreadPoolExecutor:
        raise NotImplementedError

    def execute[** ARG](self, func: Callable[ARG, any], *args: ARG):
        self.executor().submit(self._task, func, *args)

    def _task(self, func: Callable[[...], any], *args):
        # noinspection PyBroadException
        try:
            func(*args)
        except Exception as e:
            print(e)
            traceback.print_exc()

    def sync(self, func: Callable[[...], any] | Callable[[], any], *args):
        self.sync_tasks.put(lambda: func(*args))

    def _sync_task_timer(self):
        while not self.sync_tasks.empty():
            try:
                self.sync_tasks.get(block=False)()
            except Exception as e:
                print(e)
                traceback.print_exc()
        self.lock.acquire()
        if not self.closed:
            self.after(100, self._sync_task_timer)
        self.lock.release()

    @override
    def destroy(self):
        self.lock.acquire()
        self.closed = True
        self.lock.release()
        while not self.sync_tasks.empty():
            try:
                self.sync_tasks.get(block=False)()
            except Exception as e:
                print(e)
                traceback.print_exc()
        super().destroy()


class TkBase[W: 'WindowBase'](
    ElementContainer[tkinter.Tk, W],
    ThreadBase[tkinter.Tk],
    ABC,
):

    def __init__(self, executor: ThreadPoolExecutor):
        super().__init__(tkinter.Tk())
        self.min_size(200, 50)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self._executor = executor

    @override
    def executor(self) -> ThreadPoolExecutor:
        return self._executor

    def on_close(self):
        self.destroy()

    def protocol(self, name: str, func: Callable[[], object | None]):
        self.element.wm_protocol(name, func)

    def lift(self):
        self.element.tkraise()

    def most_front(self, is_enable: bool) -> Self:
        self.element.wm_attributes("-topmost", is_enable)
        return self

    def focus_force(self):
        self.element.focus_force()

    def min_size(self, width: int, height: int):
        self.element.wm_minsize(
            width=width,
            height=height
        )


class WindowBase[T: 'WindowBase'](
    TkBase,
    ABC,
):
    parent: Optional['WindowBase'] = None
    _force_focus: bool = False

    def __init__(self, executor: ThreadPoolExecutor):
        super().__init__(executor)
        self.children = list[WindowBase]()

    @override
    def window(self):
        return self

    def is_force_focus(self, force: bool):
        self._force_focus = force

    def mainloop(self):
        self.after(1, self.focus_force)
        self.element.mainloop()

    @override
    def _on_focus(self, event):
        self.focus_force_child()
        super()._on_focus(event)

    def focus_force_child(self):
        reversed_list: list['WindowBase'] = [*self.children]
        reversed_list.reverse()
        for child in reversed_list:
            child: 'WindowBase'
            if not child._force_focus:
                continue
            child.focus_force()
            break

    @override
    def destroy(self):
        for child in self.children:
            child.destroy()

        parent = self.parent
        if parent is not None:
            if parent.children.count(self) != 0:
                parent.children.remove(self)
        super().destroy()

    def child_window(self, child: 'WindowBase'):
        self.children.append(child)
        child.parent = self


class FrameBase[W: WindowBase](
    ElementContainer[tkinter.Frame, W],
    GridBase[tkinter.Frame],
    PackBase[tkinter.Frame],
    MiscBase[tkinter.Frame],
    ABC
):
    def __init__(self, parent: ElementContainer[Any, W]):
        super().__init__(tkinter.Frame(parent.element))
        self.parent = parent

    @override
    def window(self) -> W:
        return self.parent.window()

    def bg(self, color: str):
        self.element.configure(background=color)
        return self

    def size(self, width: int, height: int):
        self.element.configure(width=width, height=height)
        self.element.pack_propagate(False)
        return self


class CanvasBase[W: WindowBase](
    ElementContainer[tkinter.Canvas, W],
    GridBase[tkinter.Canvas],
    PackBase[tkinter.Canvas],
    MiscBase[tkinter.Canvas],
    ABC
):
    def __init__(self, parent: ElementContainer[Any, W]):
        super().__init__(tkinter.Canvas(parent.element))
        self.parent = parent

    @override
    def window(self) -> W:
        return self.parent.window()

    def bg(self, color: str):
        self.element.configure(background=color)
        return self

    def size(self, width: int, height: int):
        self.element.configure(width=width, height=height)
        self.element.pack_propagate(False)
        return self

    def y_scroll(self):
        scrollbar = tkinter.Scrollbar(self.element, command=self.element.yview)
        self.element.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tkinter.RIGHT, fill=tkinter.Y)

    def create_window(self, x: int, y: int, window: FrameBase):
        self.element.create_window((x, y), window=window.element)


class Canvas(CanvasBase):
    pass


class Button(
    GridBase[ttk.Button],
    PackBase[ttk.Button],
    MiscBase[ttk.Button],
):

    def __init__(self, parent: ElementContainer, text: str):
        super().__init__(ttk.Button(parent.element, text=text))
        self.parent = parent

    def on_click_execute(self, func: Callable[[any], any], *args) -> Self:
        self.add_on_left_click(lambda: self.parent.window().execute(func, *args))
        return self


class Entry(
    GridBase[ttk.Entry],
    PackBase[ttk.Entry],
    MiscBase[ttk.Entry],
):

    def __init__(self, parent: ElementContainer):
        super().__init__(ttk.Entry(parent.element))
        self.parent = parent

    def value(self):
        return self.element.get()


class Label(
    GridBase[tkinter.Label],
    PackBase[tkinter.Label],
    MiscBase[tkinter.Label],
):

    def __init__(self, parent: ElementContainer, text: str):
        super().__init__(tkinter.Label(parent.element, text=text))
        self.parent = parent

    def width(self, width: int):
        self.element.configure(width=width)

    def bg(self, color: str):
        self.element.configure(background=color)
        return self


class LabelEntry[T: ElementContainer](
    FrameBase[T]
):
    def __init__(self, parent: T, text: str):
        super().__init__(parent)
        self.label_ = self.label(text).pack()
        self.entry_ = self.entry().pack()

    def child_side(self, side: SideType):
        self.label_.side(side)
        self.entry_.side(side)
        return self

    def label_width(self, width: int):
        self.label_.width(width)
        return self
