version ?= "dev"
image_repo ?= "mirrors.tencent.com/nodeman"

build-family-bucket:
	docker build -f support-files/kubernetes/images/family_bucket/Dockerfile -t ${image_repo}/bk-nodeman:${version} .

push-family-bucket:
	docker push ${image_repo}/bk-nodeman:${version}
