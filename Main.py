"""
main.py
-------
This is the file you RUN. It is the Tkinter GUI for the Travel Agent.

Before running this for the first time:
    1. Make sure MySQL is running.
    2. Run:  python db_setup.py       (only needed once, or any time you
                                        want a fresh database -- see the
                                        note at the top of db_setup.py)
    3. Run:  python main.py

Screens (each is a Tkinter Frame that we swap in and out of the same window):
    1. LoginFrame   - pick / create a username (for favourites)
    2. SearchFrame  - enter budget, days, travellers, region, split;
                       also opens the Currency Converter
    3. ResultsFrame - shows matching destinations + Save to Favourites
    4. FavouritesFrame - shows everything this user has saved

Popup windows (opened on top of the above, not part of the frame-swap system):
    - CurrencyConverterWindow - convert an amount between 5 currencies
"""

import tkinter as tk
from tkinter import ttk, messagebox

import core_logic
import api_utils
from core_logic import connect_db


class TravelAgentApp(tk.Tk):
    """The main application window. Holds shared state and swaps frames."""

    def __init__(self):
        super().__init__()
        self.title("Travel Agent")
        self.geometry("800x600")

        # Shared state used across frames
        self.connection = None
        self.cursor = None
        self.user_id = None
        self.username = None
        self.last_results = []  # destinations found by the last search

        self._connect_to_database()

        # container that holds whichever frame is currently visible
        self.container = tk.Frame(self)
        self.container.pack(fill="both", expand=True)

        self.frames = {}
        for FrameClass in (LoginFrame, SearchFrame, ResultsFrame, FavouritesFrame):
            frame = FrameClass(self.container, self)
            self.frames[FrameClass.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.show_frame("LoginFrame")

    def _connect_to_database(self):
        """Connects to MySQL once when the app starts. Shows an error and
        exits cleanly if it can't connect, instead of crashing with a
        confusing traceback."""
        try:
            self.connection = connect_db()
            self.cursor = self.connection.cursor()
        except ConnectionError as error:
            messagebox.showerror("Database Error", str(error))
            self.destroy()
            raise SystemExit

    def show_frame(self, name):
        frame = self.frames[name]
        if hasattr(frame, "on_show"):
            frame.on_show()
        frame.tkraise()

    def on_closing(self):
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        self.destroy()


class LoginFrame(tk.Frame):
    """First screen: type a username. Existing usernames just log back in."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        tk.Label(self, text="Welcome to the Travel Agent",
                  font=("Arial", 18, "bold")).pack(pady=40)
        tk.Label(self, text="Enter a username (used to remember your favourites):",
                  font=("Arial", 11)).pack(pady=5)

        self.username_entry = tk.Entry(self, font=("Arial", 12), width=30)
        self.username_entry.pack(pady=10)
        self.username_entry.bind("<Return>", lambda event: self.continue_clicked())

        tk.Button(self, text="Continue", font=("Arial", 11),
                  command=self.continue_clicked).pack(pady=20)

    def continue_clicked(self):
        username = self.username_entry.get().strip()
        if not username:
            messagebox.showwarning("Missing Username", "Please enter a username.")
            return
        try:
            user_id = core_logic.get_or_create_user(self.app.cursor, self.app.connection, username)
            self.app.user_id = user_id
            self.app.username = username
            self.app.show_frame("SearchFrame")
        except Exception as error:
            messagebox.showerror("Error", f"Could not log in: {error}")


class SearchFrame(tk.Frame):
    """Second screen: enter budget, days, travellers and (optional) filters."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        tk.Label(self, text="Plan Your Holiday", font=("Arial", 16, "bold")).grid(
            row=0, column=0, columnspan=2, pady=15)

        # --- required inputs ---
        self.budget_entry = self._add_row(1, "Total Budget (INR):")
        self.days_entry = self._add_row(2, "Number of Days:")
        self.travellers_entry = self._add_row(3, "Number of Travellers:")

        # --- optional: destination type ---
        tk.Label(self, text="Destination Type:").grid(row=4, column=0, sticky="e", padx=10, pady=5)
        self.dest_type_var = tk.StringVar(value="Any")
        ttk.Combobox(self, textvariable=self.dest_type_var,
                     values=["Any", "domestic", "international"], state="readonly",
                     width=27).grid(row=4, column=1, padx=10, pady=5)

        # --- optional: region ---
        tk.Label(self, text="Region (optional):").grid(row=5, column=0, sticky="e", padx=10, pady=5)
        self.region_var = tk.StringVar(value="Any")
        self.region_combo = ttk.Combobox(self, textvariable=self.region_var,
                                          values=["Any"], state="readonly", width=27)
        self.region_combo.grid(row=5, column=1, padx=10, pady=5)

        # --- optional: customise budget split ---
        self.customise_var = tk.BooleanVar(value=False)
        tk.Checkbutton(self, text="Customise budget split (transit / stay / food / misc %)",
                        variable=self.customise_var,
                        command=self.toggle_split_fields).grid(
            row=6, column=0, columnspan=2, pady=(15, 5))

        self.split_frame = tk.Frame(self)
        self.split_frame.grid(row=7, column=0, columnspan=2)
        self.transit_pct_entry = self._add_split_row(0, "Transit %:")
        self.stay_pct_entry = self._add_split_row(1, "Stay %:")
        self.food_pct_entry = self._add_split_row(2, "Food %:")
        self.misc_pct_entry = self._add_split_row(3, "Misc %:")
        self.split_frame.grid_remove()  # hidden until checkbox is ticked

        tk.Button(self, text="Search Destinations", font=("Arial", 12, "bold"),
                  bg="#4CAF50", fg="white", command=self.search_clicked).grid(
            row=8, column=0, columnspan=2, pady=25)

        # --- bottom button row: favourites + currency converter ---
        bottom_bar = tk.Frame(self)
        bottom_bar.grid(row=9, column=0, columnspan=2)
        tk.Button(bottom_bar, text="View My Favourites",
                  command=lambda: app.show_frame("FavouritesFrame")).pack(side="left", padx=5)
        tk.Button(bottom_bar, text="Currency Converter",
                  command=self.open_currency_converter).pack(side="left", padx=5)

    def _add_row(self, row, label_text):
        tk.Label(self, text=label_text).grid(row=row, column=0, sticky="e", padx=10, pady=5)
        entry = tk.Entry(self, width=30)
        entry.grid(row=row, column=1, padx=10, pady=5)
        return entry

    def _add_split_row(self, row, label_text):
        tk.Label(self.split_frame, text=label_text).grid(row=row, column=0, sticky="e", padx=5, pady=3)
        entry = tk.Entry(self.split_frame, width=10)
        entry.insert(0, "0")
        entry.grid(row=row, column=1, padx=5, pady=3)
        return entry

    def toggle_split_fields(self):
        if self.customise_var.get():
            self.split_frame.grid()
        else:
            self.split_frame.grid_remove()

    def open_currency_converter(self):
        CurrencyConverterWindow(self.app)

    def on_show(self):
        """Called every time this frame becomes visible; refreshes the region list."""
        try:
            regions = core_logic.get_all_regions(self.app.cursor)
            self.region_combo["values"] = ["Any"] + regions
        except Exception as error:
            messagebox.showerror("Error", f"Could not load regions: {error}")

    def search_clicked(self):
        # ---- validate inputs (all error handling lives here) ----
        try:
            total_budget = float(self.budget_entry.get())
            days = int(self.days_entry.get())
            travellers = int(self.travellers_entry.get())
        except ValueError:
            messagebox.showerror("Invalid Input",
                                  "Budget must be a number, and days/travellers must be whole numbers.")
            return

        if total_budget <= 0 or days <= 0 or travellers <= 0:
            messagebox.showerror("Invalid Input", "Budget, days and travellers must all be greater than 0.")
            return

        try:
            if self.customise_var.get():
                transit_pct = float(self.transit_pct_entry.get())
                stay_pct = float(self.stay_pct_entry.get())
                food_pct = float(self.food_pct_entry.get())
                misc_pct = float(self.misc_pct_entry.get())
            else:
                transit_pct = stay_pct = food_pct = misc_pct = None

            budget_split = core_logic.calculate_budget_split(
                total_budget, transit_pct, stay_pct, food_pct, misc_pct)
        except ValueError as error:
            messagebox.showerror("Invalid Budget Split", str(error))
            return

        region = None if self.region_var.get() == "Any" else self.region_var.get()
        dest_type = None if self.dest_type_var.get() == "Any" else self.dest_type_var.get()

        try:
            results = core_logic.search_destinations(
                self.app.cursor, days, travellers, budget_split, region, dest_type)
        except Exception as error:
            messagebox.showerror("Search Error", f"Something went wrong while searching: {error}")
            return

        # attach the search context to each result (needed to save favourites later)
        for dest in results:
            dest["days"] = days
            dest["travellers"] = travellers

        self.app.last_results = results
        if not results:
            messagebox.showinfo("No Matches",
                                 "No destinations fit that budget. Try increasing the budget "
                                 "or changing the number of days/travellers.")
            return

        self.app.show_frame("ResultsFrame")


class ResultsFrame(tk.Frame):
    """Third screen: shows every matching destination with full details."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        tk.Label(self, text="Recommended Destinations", font=("Arial", 16, "bold")).pack(pady=10)

        top_bar = tk.Frame(self)
        top_bar.pack(fill="x", padx=10)
        tk.Button(top_bar, text="< Back to Search",
                  command=lambda: app.show_frame("SearchFrame")).pack(side="left")

        # Scrollable area, because there can be many results with lots of detail
        canvas = tk.Canvas(self)
        scrollbar = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.list_frame = tk.Frame(canvas)

        self.list_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")

    def on_show(self):
        # clear old results before drawing the new ones
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        for destination in self.app.last_results:
            self._add_destination_card(destination)

    def _add_destination_card(self, dest):
        card = tk.LabelFrame(self.list_frame, text=dest["name"], font=("Arial", 13, "bold"),
                              padx=10, pady=10)
        card.pack(fill="x", padx=5, pady=8)

        tk.Label(card, text=dest["description"], wraplength=650, justify="left").pack(anchor="w")

        # --- NEW: Why Recommended (rule-based, no AI) ---
        if dest.get("why_recommended"):
            reasons_text = "\n".join(f"   + {reason}" for reason in dest["why_recommended"])
            tk.Label(card, text="Why Recommended:\n" + reasons_text,
                      justify="left", fg="#0a5a2a").pack(anchor="w", pady=(6, 0))

        # All destination prices are stored in INR; no exchange-rate note is needed.
        rate_note = ""
        cost_text = (
            f"Transit: Rs {dest['transit_total_inr']:.0f}   |   "
            f"Stay: Rs {dest['stay_total_inr']:.0f}   |   "
            f"Food: Rs {dest['food_total_inr']:.0f}   |   "
            f"Misc: Rs {dest['misc_total_inr']:.0f}"
        )
        tk.Label(card, text=cost_text, fg="#333").pack(anchor="w", pady=(5, 0))
        tk.Label(card, text=f"TOTAL: Rs {dest['grand_total_inr']:.0f}{rate_note}",
                  font=("Arial", 11, "bold"), fg="#1a7a1a").pack(anchor="w")

        # --- NEW: Hotel Recommendation Engine (shown before the full hotel list) ---
        recommended_hotels = core_logic.recommend_hotels(dest["hotels"])
        if recommended_hotels:
            rec_lines = []
            for badge, (hotel_name, price, rating) in recommended_hotels.items():
                rec_lines.append(f"   {badge}: {hotel_name} - Rs {price:.0f}/night (rating {rating})")
            tk.Label(card, text="Recommended Hotels:\n" + "\n".join(rec_lines),
                      justify="left", font=("Arial", 10, "bold"), fg="#8a5a00").pack(anchor="w", pady=(8, 0))

        if dest["hotels"]:
            hotel_lines = "\n".join(f"   - {name}: Rs {price:.0f}/night (rating {rating})"
                                     for name, price, rating in dest["hotels"])
            tk.Label(card, text="Hotel options:\n" + hotel_lines, justify="left").pack(anchor="w", pady=(5, 0))

        if dest["local_spots"]:
            spot_lines = "\n".join(f"   - {name}: approx Rs {cost:.0f}"
                                    for name, cost in dest["local_spots"])
            tk.Label(card, text="Local sight-seeing:\n" + spot_lines, justify="left").pack(anchor="w", pady=(5, 0))

        # --- button row: Save to Favourites ---
        button_bar = tk.Frame(card)
        button_bar.pack(anchor="e", pady=(10, 0))
        tk.Button(button_bar, text="Save to Favourites",
                  command=lambda d=dest: self.save_favourite(d)).pack(side="left")

    def save_favourite(self, destination):
        try:
            core_logic.add_favourite(self.app.cursor, self.app.connection, self.app.user_id, destination)
            messagebox.showinfo("Saved", f"{destination['name']} was saved to your favourites!")
        except Exception as error:
            messagebox.showerror("Error", f"Could not save favourite: {error}")


class FavouritesFrame(tk.Frame):
    """Fourth screen: shows every package this user previously saved."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        tk.Label(self, text="My Favourite Packages", font=("Arial", 16, "bold")).pack(pady=10)

        top_bar = tk.Frame(self)
        top_bar.pack(fill="x", padx=10)
        tk.Button(top_bar, text="< Back to Search",
                  command=lambda: app.show_frame("SearchFrame")).pack(side="left")

        columns = ("name", "days", "travellers", "total", "saved_on")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=15)
        for col, text, width in [
            ("name", "Destination", 150), ("days", "Days", 60), ("travellers", "Travellers", 80),
            ("total", "Total Cost (INR)", 130), ("saved_on", "Saved On", 150)
        ]:
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        tk.Button(self, text="Remove Selected Favourite", command=self.remove_selected).pack(pady=5)

        # keeps track of fav_id for each row shown, since Treeview only stores what we tell it
        self.row_to_fav_id = {}

    def on_show(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.row_to_fav_id.clear()

        try:
            favourites = core_logic.get_favourites(self.app.cursor, self.app.user_id)
        except Exception as error:
            messagebox.showerror("Error", f"Could not load favourites: {error}")
            return

        if not favourites:
            self.tree.insert("", "end", values=("No favourites saved yet.", "", "", "", ""))
            return

        for (fav_id, name, days, travellers, total_budget,
             transit, stay, food, misc, saved_on) in favourites:
            row_id = self.tree.insert("", "end", values=(
                name, days, travellers, f"{total_budget:.0f}", str(saved_on)))
            self.row_to_fav_id[row_id] = fav_id

    def remove_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Nothing Selected", "Please select a favourite to remove.")
            return
        row_id = selected[0]
        fav_id = self.row_to_fav_id.get(row_id)
        if fav_id is None:
            return
        try:
            core_logic.remove_favourite(self.app.cursor, self.app.connection, fav_id)
            self.on_show()
        except Exception as error:
            messagebox.showerror("Error", f"Could not remove favourite: {error}")


# ---------------------------------------------------------------------
# Multi-Currency Converter popup
# ---------------------------------------------------------------------

class CurrencyConverterWindow(tk.Toplevel):
    """Popup window: convert an amount between any two supported currencies."""

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Currency Converter")
        self.geometry("380x320")

        tk.Label(self, text="Currency Converter", font=("Arial", 14, "bold")).pack(pady=15)

        tk.Label(self, text="Amount:").pack()
        self.amount_entry = tk.Entry(self, width=20)
        self.amount_entry.pack(pady=5)

        tk.Label(self, text="From:").pack()
        self.from_var = tk.StringVar(value="USD")
        ttk.Combobox(self, textvariable=self.from_var, values=api_utils.SUPPORTED_CURRENCIES,
                     state="readonly", width=17).pack(pady=5)

        tk.Label(self, text="To:").pack()
        self.to_var = tk.StringVar(value="INR")
        ttk.Combobox(self, textvariable=self.to_var, values=api_utils.SUPPORTED_CURRENCIES,
                     state="readonly", width=17).pack(pady=5)

        tk.Button(self, text="Convert", font=("Arial", 11, "bold"),
                  bg="#4CAF50", fg="white", command=self.convert_clicked).pack(pady=15)

        self.result_label = tk.Label(self, text="", font=("Arial", 11, "bold"))
        self.result_label.pack(pady=5)

        self.rate_note_label = tk.Label(self, text="", fg="#555")
        self.rate_note_label.pack()

    def convert_clicked(self):
        try:
            amount = float(self.amount_entry.get())
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid number for amount.")
            return

        from_currency = self.from_var.get()
        to_currency = self.to_var.get()

        # Same graceful-degradation pattern as the rest of the app: this
        # never raises just because the internet is unavailable.
        rates, is_live = api_utils.get_live_rates()

        try:
            converted = api_utils.convert_currency(amount, from_currency, to_currency, rates)
        except ValueError as error:
            messagebox.showerror("Error", str(error))
            return

        self.result_label.config(
            text=f"{amount:.2f} {from_currency} = {converted:.2f} {to_currency}")
        self.rate_note_label.config(
            text="Exchange rate: LIVE" if is_live else "Exchange rate: OFFLINE (fallback rate used)")


if __name__ == "__main__":
    app = TravelAgentApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
