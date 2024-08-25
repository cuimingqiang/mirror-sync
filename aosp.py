from gitlab import Gitlab
import json
import os
gl = Gitlab('http://192.168.31.164:9980', private_token='glpat-2KF3rChcSNjPzsMxuDXF', keep_base_url=True)
aosp_mirror_path = "/home/backup/mirror/aosp"
ssh = "ssh://git@192.168.31.164:9922"

def get_remote_aosp():
    groups = gl.groups.list(all=True)
    top_level_groups = [g for g in groups if not g.parent_id]
    for group in top_level_groups:
        if group.name == 'aosp':
            return group
    return None


def traverse_remote_aosp_projects(root_group, aosp_projects):
    if root_group is None:
        return
    subgroups = root_group.subgroups.list(all=True)
    if subgroups is not None:
        for subgroup in subgroups:
            traverse_remote_aosp_projects(gl.groups.get(subgroup.id), aosp_projects)
    projects = root_group.projects.list(all=True)
    for project in projects:
        name = project.name
        path = project.path_with_namespace
        name_with_namespace = project.name_with_namespace
        # print(f"name: {name}, path: {path}, name_with_namespace:{name_with_namespace}")
        aosp_projects[path + ".git"] = name


def parse_remote_aosp():
    aosp_group = get_remote_aosp()
    aosp_projects = {}
    traverse_remote_aosp_projects(aosp_group, aosp_projects)
    # print(aosp_projects)
    with open("aosp_remote.txt", "w+") as mapping:
        # for project in aosp_projects:
        #     mapping.write("name=%s, path=%s.git" % (project["name"], project["path"]))
        mapping.write(json.dumps(aosp_projects, indent=4, ensure_ascii=False))
        mapping.flush()
        mapping.close()


def traverse_local_aosp_projects(rootdir, aosp_projects):
    for subdir in os.listdir(rootdir):
        if subdir != ".repo":
            print(subdir)
            fullpath = rootdir + "/" + subdir
            if subdir.endswith(".git"):
                relationpath = fullpath[len(aosp_mirror_path) + 1 : len(fullpath)]
                # print(relationpath, fullpath)
                aosp_projects["aosp/" + relationpath] = fullpath
            else:
                traverse_local_aosp_projects(fullpath, aosp_projects=aosp_projects)


def parse_local_aosp():
    aosp_projects = {}
    traverse_local_aosp_projects(aosp_mirror_path, aosp_projects=aosp_projects)
    with open("aosp_local.txt", "w+") as mapping:
        # for project in aosp_projects:
        #     mapping.write("name=%s, path=%s.git" % (project["name"], project["path"]))
        mapping.write(json.dumps(aosp_projects, indent=4, ensure_ascii=False))
        mapping.flush()
        mapping.close()


# 1.解析gitlab仓库
# 2.解析本地mirror
def parse_aosp():
    parse_remote_aosp()
    parse_local_aosp()


# 分析gitlab和本地mirror差异
def diff_aosp():
    with open("aosp_remote.txt", "r") as mapping:
        remote_aosp_projects = json.loads(mapping.read())
    with open("aosp_local.txt", "r") as mapping:
        local_aosp_projects = json.loads(mapping.read())
    aosp_projects = {}
    left_aosp_projects = {}
    for key, value in local_aosp_projects.items():
        print(key, value)
        if remote_aosp_projects.get(key) is not None:
            aosp_projects[key] = value
            remote_aosp_projects.pop(key)
        else:   
            left_aosp_projects[key] = value
    # print(aosp_projects)
    # print(left_aosp_projects)
    # print(remote_aosp_projects)
    with open("git_need_sync.txt", "w+") as mapping:
        for key, value in aosp_projects.items():
            mapping.write("%s=%s/%s\n" % (value, ssh, key))
        mapping.flush()
        mapping.close()
    with open("git_remote.txt", "w+") as mapping:
        for key, value in left_aosp_projects.items():
            mapping.write("%s=%s/%s\n" % (value, ssh, key))
        mapping.flush()
        mapping.close()
    with open("git_gitlab.txt", "w+") as mapping:
        for key, value in remote_aosp_projects.items():
            mapping.write("%s=%s/%s\n" % (value, ssh, key))
        mapping.flush()
        mapping.close()


def traverse_remote_aosp_group(root_group, aosp_groups):
    if root_group is None:
        return
    subgroups = root_group.subgroups.list(all=True)
    if subgroups is not None:
        for subgroup in subgroups:
            traverse_remote_aosp_group(gl.groups.get(subgroup.id), aosp_groups)
            # print(subgroup)
            aosp_groups[subgroup.full_path] = subgroup
    

def get_or_create_group(aosp_groups, group_root, group_path):
    if aosp_groups.get(group_path) is not None:
        return aosp_groups[group_path]
    else:
        sub_path = group_path[:group_path.rfind("/")]
        group_name = group_path.split("/")[-1]
        # print(group_path, sub_path, group_name)
        parent_group = get_or_create_group(aosp_groups, group_root, sub_path)
        if parent_group is not None:      
            group = gl.groups.create({"name": group_name, "path": group_name, "parent_id": parent_group.id, "visibility": "public"})
            aosp_groups[group.full_path] = group
            # print(group)
            return group
        return group_root


def create_gitlab_projects():
    aosp_root = get_remote_aosp()
    aosp_groups = {}
    traverse_remote_aosp_group(aosp_root, aosp_groups)
    aosp_groups[aosp_root.full_path] = aosp_root
    # print(aosp_groups)
    with open("git_remote.txt", "r") as mapping:
        gitlab_projects = mapping.readlines()
    for project in gitlab_projects:
        project = project.strip()
        if project == "":
            continue
        print(project)
        # name = project.split("=")[0]
        path = project.split("=")[1]
        gitlab_path = path[len(ssh) + 1: len(path)]
        gitlab_name = gitlab_path.split("/")[-1]
     
        gitlab_path = gitlab_path[:-len(gitlab_name) - 1]
        gitlab_name = gitlab_name[:-4]

        print(gitlab_name, gitlab_path)
        group = get_or_create_group(aosp_groups, aosp_root, gitlab_path)
        print(gitlab_name, gitlab_path, group.full_path, group.id)
        try:
            project = gl.projects.create({"name": gitlab_name, "namespace_id": group.id, "visibility": "public"})
            print(project)
        except Exception as e:
            print(e)
        

if __name__ == "__main__":
    # parse_aosp()
    # diff_aosp()
    create_gitlab_projects()