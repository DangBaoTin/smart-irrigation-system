


def generate_train_data_view(place_id: int, time_neg: int, time_pos: int, time_step: int) -> str:
    view_name = f"train_data_{place_id}_{time_neg}_{time_pos}_{time_step}"

    query = f"""create or replace {view_name} as (\n\tselect \n\t\tld.id as log_id \n\t\t, ld.place_id \n"""

    # Generate columns for past data (negative time)
    for i in range(time_neg, 0, -time_step):
        query += f"\t\t, before_{i - 1}h.s_moist as smoist_before_{i}hour \n"

    # Generate columns for future data (positive time)
    for i in range(1, time_pos + 1, time_step):
        query += f"\t\t, after_{i}h.s_moist as next_smoist_{i}hour \n"

    query += """\t\t, ld.action \n\t\t, ld.reward \n\tfrom log_data as ld \n"""

    # Generate joins for past states
    for i in range(time_neg, 0, -time_step):
        query += f"""\tjoin env_state as before_{i - 1}h \n\t\ton ld.place_id = before_{i - 1}h.place_id \n\t\tand before_{i - 1}h.created_at = date_trunc('hour', ld.created_at - cast((ld.time_neg || ' hour') as interval)) + cast(({time_neg - i} * ld.time_step || ' hour') as interval)\n"""
    
    
    # Generate joins for future states
    for i in range(1, time_pos + 1, time_step):
        query += f"""\tjoin env_state as after_{i}h \n\t\ton ld.place_id = after_{i}h.place_id \n\t\tand after_{i}h.created_at = date_trunc('hour', ld.created_at + cast((ld.time_pos || ' hour') as interval)) - cast(({time_pos - i} * ld.time_step || ' hour') as interval)\n"""

    query += ");"
    return query.strip()


print(generate_train_data_view(0, 3, 2, 1))