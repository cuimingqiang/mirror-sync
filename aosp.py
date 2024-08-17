from gitlab import Gitlab

gl = Gitlab('http://192.168.31.164:9980', private_token='glpat-2KF3rChcSNjPzsMxuDXF', keep_base_url=True)

def get_aosp():
    groups = gl.groups.list(all=True)
    top_level_groups = [g for g in groups if not g.parent_id]
    for group in top_level_groups:
        if group.name == 'aosp':
            return group
    return None


def traverse_aosp_projects(root_group, aosp_projects):
    if root_group is None:
        return
    subgroups = root_group.subgroups.list(all=True)
    if subgroups is not None:
        for subgroup in subgroups:
            traverse_aosp_projects(gl.groups.get(subgroup.id), aosp_projects)
    projects = root_group.projects.list(all=True)
    for project in projects:
        name = project.name
        path = project.path_with_namespace
        print(f"name: {name}, path: {path}")
        aosp_projects.append({
            "name": name,
            "path": path
            })


if __name__ == "__main__":
    aosp_group = get_aosp()
    aosp_projects = []
    traverse_aosp_projects(aosp_group, aosp_projects)
    print(aosp_projects)