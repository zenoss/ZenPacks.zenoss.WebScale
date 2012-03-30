######################################################################
#
# Copyright 2011 Zenoss, Inc.  All Rights Reserved.
#
######################################################################

#==================================
NGINXVERSION=1.0.10
UPSTREAMFAIRVERSION=5f6a3b720e1cfbb9ef0258a543bf5d9f63915e20
#==================================

HERE=$(PWD)
LIBDIR=$(HERE)/lib
BUILDDIR=$(HERE)/build
TARGETDIR=$(HERE)/ZenPacks/zenoss/WebScale
PREFIXDIR=$(ZENHOME)
BINDIR=$(TARGETDIR)/bin
NGINX=$(LIBDIR)/nginx-$(NGINXVERSION).tar.gz
NGINXDIR=$(BUILDDIR)/nginx-$(NGINXVERSION)
UPSTREAMFAIR=$(LIBDIR)/nginx-upstream-fair-$(UPSTREAMFAIRVERSION).tar.gz
UPSTREAMFAIRDIR=$(BUILDDIR)/nginx-upstream-fair-$(UPSTREAMFAIRVERSION)

default: egg

egg:
	@python setup.py bdist_egg

%/.d:
	@mkdir -p $(@D)
	@touch $@

$(NGINXDIR)/.d: $(BUILDDIR)/.d
	@cd $(BUILDDIR) && tar xzf $(NGINX)
	@touch $(@)

$(UPSTREAMFAIRDIR)/.d: $(BUILDDIR)/.d
	@cd $(BUILDDIR) && tar xzf $(UPSTREAMFAIR)
	@touch $(@)

$(BINDIR)/nginx: $(BINDIR)/.d $(PREFIXDIR)/.d $(UPSTREAMFAIRDIR)/.d $(NGINXDIR)/.d
	@echo "Building nginx..."
	@cd $(NGINXDIR) && \
		./configure \
       		--prefix=$(PREFIXDIR) \
			--builddir=$(BUILDDIR) \
			--sbin-path=$(BINDIR)/nginx \
			--http-client-body-temp-path=$(PREFIXDIR)/var/nginx/tmp/client_body \
			--http-proxy-temp-path=$(PREFIXDIR)/var/nginx/tmp/proxy \
			--http-fastcgi-temp-path=$(PREFIXDIR)/var/nginx/tmp/fcgi \
			--http-uwsgi-temp-path=$(PREFIXDIR)/var/nginx/tmp/uwsgi \
			--http-scgi-temp-path=$(PREFIXDIR)/var/nginx/tmp/scgi \
			--http-log-path=$(PREFIXDIR)/log/nginx/access.log \
			--error-log-path=$(PREFIXDIR)/log/nginx/error.log \
			--with-http_ssl_module \
			--with-http_stub_status_module \
			--without-http_uwsgi_module \
			--without-http_scgi_module \
			--without-http_fastcgi_module \
			--add-module=$(UPSTREAMFAIRDIR) \
		&& make && make install 
	@echo "Cleaning up..."
	@rm -rf $(PREFIXDIR)/conf $(PREFIXDIR)/logs


build: $(BINDIR)/nginx

clean:
	@rm -rf $(BUILDDIR) dist temp
	@rm -rf $(TARGETDIR)/lib $(BINDIR)
	@rm -rf *.egg-info
	@find . -name *.pyc | xargs rm -f

.PRECIOUS: %/.d
