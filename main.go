package main

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"

	"github.com/extrame/xls"
)

type Row struct {
	MOP     string  `json:"mop"`
	Marca   string  `json:"marca"`
	Ref     string  `json:"ref"`
	Mes     string  `json:"mes"`
	Plan    float64 `json:"plan"`
	Comp    float64 `json:"comp"`
	Pend    float64 `json:"pend"`
	Section string  `json:"section"`
}

func uploadHandler(res http.ResponseWriter, req *http.Request) {
	req.ParseMultipartForm(100 << 20) // 100MB
	form := req.MultipartForm
	files := form.File["files"]
	sec := req.FormValue("section")

	for _, head := range files {
		file, err := head.Open()
		if err != nil {
			continue
		}
		path := filepath.Join("data", sec, head.Filename)
		out, err := os.Create(path)
		if err != nil {
			file.Close()
			continue
		}
		io.Copy(out, file)
		file.Close()
		out.Close()
	}
	res.Header().Set("Content-Type", "text/plain")
	res.Write([]byte("ok"))
}

func dataHandler(res http.ResponseWriter, req *http.Request) {
	secs := []string{"entrega", "pending", "cut", "wip"}
	all := []Row{}

	for _, s := range secs {
		files, _ := filepath.Glob(filepath.Join("data", s, "*.xls"))
		for _, f := range files {
			xl, err := xls.Open(f, "utf-8")
			if err != nil {
				log.Printf("Fail open %s: %v", f, err)
				continue
			}
			sheet := xl.GetSheet(0)
			if sheet == nil {
				continue
			}

			marca := "N/A"
			fn := strings.ToUpper(f)
			if strings.Contains(fn, "STOP") {
				marca = "STOP"
			} else if strings.Contains(fn, "YOYO") {
				marca = "YOYO"
			}

			for i := 1; i <= int(sheet.MaxRow); i++ {
				r := sheet.Row(i)
				if r == nil {
					continue
				}

				p, _ := strconv.ParseFloat(r.Col(8), 64)
				c, _ := strconv.ParseFloat(r.Col(10), 64)
				pe, _ := strconv.ParseFloat(r.Col(11), 64)

				all = append(all, Row{
					MOP:     r.Col(0),
					Marca:   marca,
					Ref:     r.Col(1),
					Mes:     r.Col(3),
					Plan:    p,
					Comp:    c,
					Pend:    pe,
					Section: s,
				})
			}
		}
	}
	res.Header().Set("Content-Type", "application/json")
	json.NewEncoder(res).Encode(all)
}

func main() {
	dirs := []string{"data/entrega", "data/pending", "data/cut", "data/wip"}
	for _, d := range dirs {
		os.MkdirAll(d, 0755)
	}

	http.HandleFunc("/api/upload", uploadHandler)
	http.HandleFunc("/api/data", dataHandler)
	http.Handle("/", http.FileServer(http.Dir("./public")))

	fmt.Println("Server ready → http://localhost:8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}
