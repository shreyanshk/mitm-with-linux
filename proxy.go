package main

import (
	"bytes"
	"crypto/tls"
	"fmt"
	"io"
	"io/ioutil"
	"net/http"
	"time"
)

var client = &http.Client{
	Timeout: time.Second * 10,
	Transport: &http.Transport{
		TLSClientConfig: &tls.Config{
			InsecureSkipVerify: true,
		},
	},
}

func proxy(wr http.ResponseWriter, r *http.Request) {
	var resp *http.Response
	var err error
	var req *http.Request
	b, err := ioutil.ReadAll(r.Body)
	if err != nil {
		panic(err)
	}
	r.Body.Close()
	if r.Method == http.MethodPost {
		fmt.Println(fmt.Sprintf("---> %s", b))
	}
	req, err = http.NewRequest(
		r.Method,
		"https://172.16.0.154"+r.RequestURI,
		ioutil.NopCloser(bytes.NewBuffer(b)),
	)
	for name, value := range r.Header {
		req.Header.Set(name, value[0])
	}
	resp, err = client.Do(req)
	if err != nil {
		http.Error(wr, err.Error(), http.StatusInternalServerError)
		return
	}
	defer resp.Body.Close()
	for k, v := range resp.Header {
		wr.Header().Set(k, v[0])
	}
	wr.WriteHeader(resp.StatusCode)
	io.Copy(wr, resp.Body)
}

func main() {
	fmt.Println("Starting")
	http.HandleFunc("/", proxy)
	if err := http.ListenAndServeTLS(
		":8080",
		"cert.pem",
		"key.pem",
		nil,
	); err != nil {
		fmt.Println("Stopped...")
		panic(err)
	}
	fmt.Println("Exiting")
}
