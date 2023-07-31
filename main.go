package main

import (
	"bytes"
	"encoding/json"
	"html/template"
	"io"
	"log"
	"net/http"
	"os"
	"strconv"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/go-chi/httprate"
)

type application struct {
	errorLog *log.Logger
	infoLog  *log.Logger
	tmpl     *template.Template
}

type vanityResponse struct {
	Response struct {
		SteamID string `json:"steamid"`
		Success int    `json:"success"`
	} `json:"response"`
}

type steamProfile struct {
	SteamID    string `json:"steamid"`
	Visibility int    `json:"communityvisibilitystate"`
	Name       string `json:"personaname"`
	Link       string `json:"profileurl"`
	Avatar     string `json:"avatarfull"`
	Status     int    `json:"personastate"`
	Game       string `json:"gameextrainfo"`
	GameID     string `json:"gameid"`
	LobbyID    string `json:"lobbysteamid"`
}

type summaryResponse struct {
	Response struct {
		Players []*steamProfile `json:"players"`
	} `json:"response"`
}

type templateData struct {
	Steam      string
	NoRedirect bool
	Profile    *steamProfile
}

func main() {
	errorLog := log.New(os.Stderr, "ERROR\t", log.Ldate|log.Ltime|log.Lshortfile)
	infoLog := log.New(os.Stdout, "INFO\t", log.Ldate|log.Ltime)

	tmpl, err := template.ParseFiles("./ui/tmpl.html")
	if err != nil {
		errorLog.Fatal(err)
	}

	app := &application{
		errorLog: errorLog,
		infoLog:  infoLog,
		tmpl:     tmpl,
	}

	r := chi.NewRouter()
	r.Use(middleware.RequestID)
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)
	r.Use(httprate.LimitByIP(100, 1*time.Minute))

	fileServer := http.FileServer(http.Dir("./ui/static/"))
	r.Handle("/*", http.StripPrefix("/", fileServer))

	r.Get("/", app.home)
	r.Get("/{steam:^[a-zA-Z0-9_-]*$}", app.join)

	r.MethodNotAllowed(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(405)
		w.Write([]byte("method is not valid"))
	})

	port := ":" + os.Getenv("PORT")
	infoLog.Printf("Starting server on %s", port)
	err = http.ListenAndServe(port, r)
	errorLog.Fatal(err)
}

// Handlers
func (app *application) home(w http.ResponseWriter, r *http.Request) {
	app.render(w, http.StatusOK, &templateData{})
}

func (app *application) join(w http.ResponseWriter, r *http.Request) {
	steamkey := os.Getenv("STEAMKEY")
	steam := chi.URLParam(r, "steam")
	noRedirect := r.URL.Query().Has("noredirect")

	// vanity URL to ID
	if _, err := strconv.Atoi(steam); err != nil {
		req := "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/?key=" + steamkey + "&vanityurl=" + steam
		resp, err := http.Get(req)
		if err != nil {
			app.serverError(w, err)
			return
		}
		defer resp.Body.Close()
		body, err := io.ReadAll(resp.Body)
		if err != nil {
			app.serverError(w, err)
			return
		}
		var result vanityResponse
		if err := json.Unmarshal(body, &result); err != nil {
			app.serverError(w, err)
			return
		}
		if result.Response.Success == 1 {
			steam = result.Response.SteamID
		}
	}

	req := "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key=" + steamkey + "&steamids=[" + steam + "]"
	resp, err := http.Get(req)
	if err != nil {
		app.serverError(w, err)
		return
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		app.serverError(w, err)
		return
	}
	var result summaryResponse
	if err := json.Unmarshal(body, &result); err != nil {
		app.serverError(w, err)
		return
	}

	var profile *steamProfile
	if len(result.Response.Players) > 0 {
		profile = result.Response.Players[0]
	} else {
		profile = nil // invalid steam
	}
	app.render(w, http.StatusOK, &templateData{
		Steam:      steam,
		NoRedirect: noRedirect,
		Profile:    profile,
	})
}

// Helpers
func (app *application) serverError(w http.ResponseWriter, err error) {
	// trace := fmt.Sprintf("%s\n%s", err.Error(), debug.Stack())
	app.errorLog.Output(2, err.Error())
	http.Error(w, http.StatusText(http.StatusInternalServerError), http.StatusInternalServerError)
}

func (app *application) render(w http.ResponseWriter, status int, data *templateData) {
	buf := new(bytes.Buffer)
	err := app.tmpl.Execute(buf, data)
	if err != nil {
		app.serverError(w, err)
		return
	}
	w.WriteHeader(status)
	buf.WriteTo(w)
}
