package jinja2

import (
	"bufio"
	"github.com/go-git/go-git/v5/plumbing/format/gitignore"
	"os"
	"path/filepath"
	"strings"
)

const (
	commentPrefix      = "#"
	templateIgnoreFile = ".templateignore"
)

// readIgnoreFile reads a specific git ignore file.
func (j *Jinja2) readIgnoreFile(path string, domainIn []string) (ps []gitignore.Pattern, err error) {
	domain := make([]string, len(domainIn))
	copy(domain, domainIn)

	f, err := os.Open(path)
	if err == nil {
		defer f.Close()

		scanner := bufio.NewScanner(f)
		for scanner.Scan() {
			s := scanner.Text()
			if !strings.HasPrefix(s, commentPrefix) && len(strings.TrimSpace(s)) > 0 {
				ps = append(ps, gitignore.ParsePattern(s, domain))
			}
		}
	} else if !os.IsNotExist(err) {
		return nil, err
	}

	return
}

// readPatternsRecursive reads gitignore patterns recursively traversing through the directory
// structure. The result is in the ascending order of priority (last higher).
func (j *Jinja2) readPatternsRecursive(rootDir string, domain []string) (ps []gitignore.Pattern, err error) {
	path := filepath.Join(rootDir, filepath.Join(domain...), templateIgnoreFile)
	ps, _ = j.readIgnoreFile(path, domain)

	pd := domain
	if len(domain) == 0 {
		pd = []string{"."}
	}

	var fis []os.DirEntry
	fis, err = os.ReadDir(filepath.Join(rootDir, filepath.Join(pd...)))
	if err != nil {
		return
	}

	domain2 := make([]string, len(domain)+1)
	copy(domain2, domain)

	for _, fi := range fis {
		if fi.IsDir() {
			domain2[len(domain)] = fi.Name()

			var subps []gitignore.Pattern
			subps, err = j.readPatternsRecursive(rootDir, domain2)
			if err != nil {
				return
			}

			if len(subps) > 0 {
				ps = append(ps, subps...)
			}
		}
	}

	return
}

func (j *Jinja2) readAllIgnoreFiles(rootDir string, subdir string, excludePatterns []string) ([]gitignore.Pattern, error) {
	var ret []gitignore.Pattern
	var domain []string
	var subDir2 string
	if subdir != "" {
		for _, e := range strings.Split(subdir, string(filepath.Separator)) {
			x, err := j.readIgnoreFile(filepath.Join(rootDir, subDir2, templateIgnoreFile), domain)
			if err != nil {
				return nil, err
			}
			ret = append(ret, x...)
			subDir2 = filepath.Join(subDir2, e)
			domain = append(domain, e)
		}
	}

	x, err := j.readPatternsRecursive(rootDir, domain)
	if err != nil {
		return nil, err
	}
	ret = append(ret, x...)

	for _, ep := range excludePatterns {
		p := gitignore.ParsePattern(ep, domain)
		ret = append(ret, p)
	}

	return ret, nil
}
